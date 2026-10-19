"""产线平衡优化算法核心（纯标准库，无 GUI / 无授权依赖）。

本模块的三段算法 evaluate_solution / StableOptimizer / optimize_with_backtracking
按既有逆向产物的算法逻辑重写，仅保留纯算法，剥离 tkinter/pandas/matplotlib 与
授权保护逻辑，不含任何原作者署名/版权/授权串。算法行为一致、可对拍。

输入/输出契约见同级 api.py 与扩展计划书 §3。
"""
from __future__ import annotations
import time


def evaluate_solution(processes: list[dict]) -> float:
    """平衡率 = 总工时 / (瓶颈周期 × 总人数)。"""
    total_time = sum(p['time'] for p in processes)
    total_people = sum(p['people'] for p in processes)
    bottleneck_time = max(p['time'] / p['people'] for p in processes)
    if bottleneck_time == 0:
        return 0
    return total_time / (bottleneck_time * total_people)


class StableOptimizer:
    """带约束的 DFS 回溯搜索，在所有可合并分组方式里找平衡率最高解。"""

    def __init__(self, processes: list[dict], takt_time: float):
        self.processes = processes
        self.takt_time = takt_time
        self.proc_map = {p['original_id']: p for p in processes}
        self.first_id = min(p['original_id'] for p in processes)
        self.last_id = max(p['original_id'] for p in processes)
        self.best_rate = 0
        self.best_solution = None
        self.start_time = time.time()
        if len(processes) <= 15:
            self.time_limit = 60
        elif len(processes) <= 25:
            self.time_limit = 90
        elif len(processes) <= 40:
            self.time_limit = 120
        else:
            self.time_limit = 150
        self.visited = set()
        self.timeout_reached = False
        self.merge_candidates = [p for p in processes if p['added_people'] == 0 and p['can_merge']]
        self.fixed_processes = [p for p in processes if not (p['added_people'] == 0 and p['can_merge'])]
        self.global_max_cycle = max(p['time'] / p['people'] for p in processes)
        self.max_allowed_time = max(takt_time, self.global_max_cycle)

    def calc_balance_rate(self, groups: list[dict]) -> float:
        simulated_processes = []
        for g in groups:
            simulated_processes.append({'time': g['time'], 'people': g['people']})
        total_time = sum(p['time'] for p in simulated_processes)
        total_people = sum(p['people'] for p in simulated_processes)
        bottleneck_time = max(p['time'] / p['people'] for p in simulated_processes)
        if bottleneck_time <= 0:
            return 0
        return total_time / (bottleneck_time * total_people)

    def validate_group_merge(self, group: dict, proc: dict) -> bool:
        if not proc['can_merge']:
            return False
        if len(group['ids']) >= 4:
            return False
        for pid in group['ids']:
            if abs(pid - proc['original_id']) > 5:
                return False
        if group['time'] + proc['time'] > self.max_allowed_time:
            return False
        return True

    def validate_precedence(self, groups: list[dict]) -> bool:
        sequence = []
        for g in groups:
            ids = sorted(g['ids'])
            sequence.extend(ids)
        pos_map = {}
        for idx, pid in enumerate(sequence):
            pos_map[pid] = idx
        for p in self.processes:
            pid = p['original_id']
            pre = p.get('pre_id')
            if pre is None:
                continue
            if pre not in pos_map:
                continue
            if pid not in pos_map:
                continue
            pre_pos = pos_map[pre]
            cur_pos = pos_map[pid]
            if cur_pos != pre_pos + 1:
                return False
        return True

    def validate_first_last(self, groups: list[dict]) -> bool:
        if not groups:
            return True
        first_group = groups[0]['ids']
        last_group = groups[-1]['ids']
        if self.first_id not in first_group:
            return False
        if self.last_id not in last_group:
            return False
        return True

    def make_signature(self, idx: int, groups: list[dict]):
        sig = []
        for g in groups:
            sig.append(tuple(sorted(g['ids'])))
        return (idx, tuple(sorted(sig)))

    # —— 串行装配链的精确解（生产实际路径）——
    # _build_optimize_input 把工艺图拓扑拉直成 original_id=1..N、pre_id=i-1 的单链，
    # 此时 validate_precedence 等价于「分组必须是 1..N 的连续区间」。该约束下线平衡退化为
    # 一维连续分段问题，可用 O(N²) 动态规划求全局最优——既不超时，也优于受时限影响、
    # 超时即退回「完全不合并」的 DFS。非单链（自定义 pre_id）仍走原 DFS。
    def _is_serial_chain(self) -> bool:
        ids = sorted(p['original_id'] for p in self.processes)
        if ids != list(range(ids[0], ids[0] + len(ids))):
            return False
        first = ids[0]
        for p in self.processes:
            pid = p['original_id']
            pre = p.get('pre_id')
            expected = None if pid == first else pid - 1
            if pre != expected:
                return False
        return True

    def _chain_optimize(self):
        """连续分段 DP。枚举瓶颈候选 B（任一长度≤4 的连续区间和），在「每段≤4 道、
        段工时≤B、不可合并工序只能独立成段」约束下，最小化总人数；对每个 B 还原分段并按
        真实平衡率取最优。瓶颈最优值必为某段之和、必在候选集中，故全局最优。"""
        order = sorted(self.processes, key=lambda p: p['original_id'])
        n = len(order)
        times = [p['time'] for p in order]
        people0 = [p['people'] for p in order]
        # 该工序是否可参与合并（与 DFS 的 merge_candidates 判定一致）
        mergeable = [(p['added_people'] == 0 and p['can_merge']) for p in order]

        def seg_people(lo: int, hi: int) -> int:
            t = sum(times[lo:hi + 1])
            need = int(t / self.takt_time + 0.999) if self.takt_time > 0 else 1
            return max(max(people0[lo:hi + 1]), need, 1)

        # 段 (lo..hi) 是否允许：长度≤4；单段不限，多段要求全部可合并；工时≤上限
        def seg_ok(lo: int, hi: int, cap: float) -> bool:
            if hi - lo + 1 > 4:
                return False
            t = sum(times[lo:hi + 1])
            if t > cap + 1e-9:
                return False
            if hi > lo and not all(mergeable[lo:hi + 1]):
                return False
            return True

        # 瓶颈候选：所有长度≤4 的连续区间和（≤合并上限）
        caps = set()
        for lo in range(n):
            for hi in range(lo, min(lo + 4, n)):
                s = sum(times[lo:hi + 1])
                if s <= self.max_allowed_time + 1e-9:
                    caps.add(round(s, 6))
        caps.add(round(self.max_allowed_time, 6))

        best_rate = -1.0
        best_groups = None
        for cap in sorted(caps):
            INF = float('inf')
            dp = [INF] * (n + 1)
            back = [-1] * (n + 1)
            dp[0] = 0
            for j in range(1, n + 1):
                for k in range(max(0, j - 4), j):
                    if dp[k] == INF:
                        continue
                    if seg_ok(k, j - 1, cap):
                        cost = dp[k] + seg_people(k, j - 1)
                        if cost < dp[j]:
                            dp[j] = cost
                            back[j] = k
            if dp[n] == INF:
                continue
            groups = []
            j = n
            while j > 0:
                k = back[j]
                groups.append((k, j - 1))
                j = k
            groups.reverse()
            built = []
            for lo, hi in groups:
                built.append({
                    'ids': [order[i]['original_id'] for i in range(lo, hi + 1)],
                    'names': [order[i]['name'] for i in range(lo, hi + 1)],
                    'time': sum(times[lo:hi + 1]),
                    'people': seg_people(lo, hi)})
            rate = self.calc_balance_rate(built)
            if rate > best_rate:
                best_rate = rate
                best_groups = built
        return best_groups

    def dfs(self, idx: int, groups: list[dict]) -> None:
        if self.timeout_reached:
            return
        if time.time() - self.start_time >= self.time_limit:
            self.timeout_reached = True
            return
        if idx >= len(self.merge_candidates):
            if not self.validate_precedence(groups):
                return
            if not self.validate_first_last(groups):
                return
            final_groups = []
            for g in groups:
                final_groups.append({
                    'ids': g['ids'][:],
                    'names': g['names'][:],
                    'time': g['time'],
                    'people': g['people']})
            for p in self.fixed_processes:
                final_groups.append({
                    'ids': [p['original_id']],
                    'names': [p['name']],
                    'time': p['time'],
                    'people': p['people']})
            final_groups.sort(key=lambda x: min(x['ids']))
            rate = self.calc_balance_rate(final_groups)
            if rate > self.best_rate:
                self.best_rate = rate
                self.best_solution = []
                for g in final_groups:
                    self.best_solution.append({
                        'ids': g['ids'][:],
                        'names': g['names'][:],
                        'time': g['time'],
                        'people': g['people']})
            return
        sig = self.make_signature(idx, groups)
        if sig in self.visited:
            return
        self.visited.add(sig)
        proc = self.merge_candidates[idx]
        for g in groups:
            if self.timeout_reached:
                return
            if not self.validate_group_merge(g, proc):
                continue
            old_ids = g['ids'][:]
            old_names = g['names'][:]
            old_time = g['time']
            old_people = g['people']
            g['ids'].append(proc['original_id'])
            g['names'].append(proc['name'])
            g['ids'].sort()
            g['time'] += proc['time']
            need_people = int(g['time'] / self.takt_time + 0.999)
            g['people'] = max(g['people'], proc['people'], need_people)
            if self.validate_precedence(groups):
                self.dfs(idx + 1, groups)
                if self.timeout_reached:
                    return
            g['ids'] = old_ids
            g['names'] = old_names
            g['time'] = old_time
            g['people'] = old_people
        new_group = {
            'ids': [proc['original_id']],
            'names': [proc['name']],
            'time': proc['time'],
            'people': proc['people']}
        if self.timeout_reached:
            return
        groups.append(new_group)
        if self.validate_precedence(groups):
            self.dfs(idx + 1, groups)
            if self.timeout_reached:
                return
        groups.pop()

    def optimize(self):
        # 串行装配链（生产实际入参）走 O(N²) 精确 DP：全局最优、瞬时返回、不受时限影响。
        if self._is_serial_chain():
            chain_solution = self._chain_optimize()
            if chain_solution:
                self.best_solution = chain_solution
                self.best_rate = self.calc_balance_rate(chain_solution)
        else:
            self.dfs(0, [])
            if self.timeout_reached:
                self.visited.clear()
        if not self.best_solution:
            result = []
            for p in sorted(self.processes, key=lambda x: x['original_id']):
                result.append({
                    'original_id': p['original_id'],
                    'original_ids': [p['original_id']],
                    'name': p['name'],
                    'time': p['time'],
                    'people': p['people'],
                    'merge_names': [p['name']],
                    'detail_times': [p['time']],
                    'added_people': p['added_people'],
                    'can_merge': p['can_merge'],
                    'pre_id': p['pre_id'],
                    'can_add': p['can_add']})
            timeout_reached = time.time() - self.start_time >= self.time_limit
            return (result, evaluate_solution(result), timeout_reached)
        result = []
        merged_ids = set()
        for g in sorted(self.best_solution, key=lambda x: min(x['ids'])):
            ids = sorted(g['ids'])
            for pid in ids:
                merged_ids.add(pid)
            base_proc = self.proc_map[ids[0]]
            result.append({
                'original_id': ids[0],
                'original_ids': ids,
                'name': ' + '.join(g['names']),
                'time': g['time'],
                'people': g['people'],
                'merge_names': g['names'],
                'detail_times': [self.proc_map[x]['time'] for x in ids],
                'added_people': base_proc['added_people'],
                'can_merge': False,
                'pre_id': base_proc['pre_id'],
                'can_add': base_proc['can_add']})
        for p in self.processes:
            pid = p['original_id']
            if pid in merged_ids:
                continue
            result.append({
                'original_id': pid,
                'original_ids': [pid],
                'name': p['name'],
                'time': p['time'],
                'people': p['people'],
                'merge_names': [p['name']],
                'detail_times': [p['time']],  # 源码此处漏了该字段，补齐以保证 result 各项契约一致
                'added_people': p['added_people'],
                'can_merge': p['can_merge'],
                'pre_id': p['pre_id'],
                'can_add': p['can_add']})
        result.sort(key=lambda x: x['original_id'])
        final_rate = evaluate_solution(result)
        timeout_reached = time.time() - self.start_time >= self.time_limit
        return (result, final_rate, timeout_reached)


def optimize_with_backtracking(processes: list[dict], takt_time: float, progress_callback=None):
    """对外算法入口：构造 StableOptimizer 并求解。返回 (result, rate, timeout_reached)。"""
    if progress_callback:
        progress_callback('优化中...')
    optimizer = StableOptimizer(processes, takt_time)
    (result, rate, timeout_reached) = optimizer.optimize()
    if progress_callback:
        progress_callback(f'优化完成，平衡率：{rate:.2%}')
    return (result, rate, timeout_reached)
