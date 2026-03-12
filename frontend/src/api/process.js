
/**
 * 进程管理 API
 */
import request from './request'

/**
 * 获取进程状态
 * @returns {Promise}
 */
export function getProcessStatus() {
  return request.get('/process/status')
}

/**
 * 启动服务
 * @returns {Promise}
 */
export function startService() {
  return request.post('/process/start')
}

/**
 * 停止服务
 * @returns {Promise}
 */
export function stopService() {
  return request.post('/process/stop')
}

/**
 * 重启服务
 * @returns {Promise}
 */
export function restartService() {
  return request.post('/process/restart')
}

/**
 * 获取系统资源使用情况
 * @returns {Promise}
 */
export function getSystemStats() {
  return request.get('/process/stats')
}
