/** 与 FastAPI GET /health 响应保持一致的前端类型。 */
export interface HealthResponse {
  status: 'ok'
  service: string
  version: string
}
