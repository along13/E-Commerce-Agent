import type { HealthResponse } from '../types/health'

// Vite 环境变量在构建时注入；移除末尾斜杠以统一拼接 API 路径。
export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

/** 请求后端健康检查，并将超时、HTTP 错误和无效响应转换成可读错误。 */
export async function fetchHealth(): Promise<HealthResponse> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(`${apiBaseUrl}/health`, { signal: controller.signal })
    if (!response.ok) throw new Error(`健康检查失败（HTTP ${response.status}）`)
    // 先按 unknown 校验网络响应，避免直接信任未验证的 JSON 结构。
    const data: unknown = await response.json()
    if (typeof data !== 'object' || data === null ||
        !('status' in data) || data.status !== 'ok' ||
        !('service' in data) || typeof data.service !== 'string' ||
        !('version' in data) || typeof data.version !== 'string') {
      throw new Error('后端返回的健康检查格式不正确')
    }
    return data as HealthResponse
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('连接超时，请确认后端已启动。')
    }
    throw err
  } finally {
    window.clearTimeout(timeout)
  }
}
