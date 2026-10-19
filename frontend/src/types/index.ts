export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PageResult<T = any> {
  list: T[]
  total: number
  page: number
  pageSize: number
}

export interface UserInfo {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  avatar?: string
  createdAt: string
}

export interface ChartTemplate {
  id: string
  name: string
  engine: 'vue-component' | 'matplotlib'
  category: string
  description: string
  tags: string[]
  exportFormats: string[]
  sortOrder: number
  path: string
}

export interface ChartRecord {
  id: number
  title: string
  templateId: string
  engine: string
  data: Record<string, any>
  createdAt: string
  updatedAt: string
}
