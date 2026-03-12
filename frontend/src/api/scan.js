
/**
 * 扫描管理 API
 */
import request from './request'

/**
 * 获取扫描任务列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.status - 任务状态
 * @returns {Promise}
 */
export function getScanTasks(params) {
  return request.get('/scan/tasks', { params })
}

/**
 * 获取扫描任务详情
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function getScanTask(taskId) {
  return request.get(`/scan/tasks/${taskId}`)
}

/**
 * 创建扫描任务
 * @param {Object} data - 任务数据
 * @param {string} data.target_path - 扫描路径
 * @param {string} data.scan_type - 扫描类型 (full/incremental)
 * @param {boolean} data.recursive - 是否递归扫描
 * @returns {Promise}
 */
export function createScanTask(data) {
  return request.post('/scan/tasks', data)
}

/**
 * 停止扫描任务
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function stopScanTask(taskId) {
  return request.post(`/scan/tasks/${taskId}/stop`)
}

/**
 * 获取扫描路径列表
 * @returns {Promise}
 */
export function getScanPaths() {
  return request.get('/scan/paths')
}

/**
 * 添加扫描路径
 * @param {Object} data - 路径数据
 * @param {string} data.path - 路径
 * @param {boolean} data.recursive - 是否递归
 * @param {boolean} data.enabled - 是否启用
 * @returns {Promise}
 */
export function addScanPath(data) {
  return request.post('/scan/paths', data)
}

/**
 * 更新扫描路径
 * @param {number} id - 路径ID
 * @param {Object} data - 路径数据
 * @returns {Promise}
 */
export function updateScanPath(id, data) {
  return request.put(`/scan/paths/${id}`, data)
}

/**
 * 删除扫描路径
 * @param {number} id - 路径ID
 * @returns {Promise}
 */
export function deleteScanPath(id) {
  return request.delete(`/scan/paths/${id}`)
}

/**
 * 获取扫描历史
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 返回数量限制
 * @param {number} params.offset - 偏移量
 * @returns {Promise}
 */
export function getScanHistory(params) {
  return request.get('/scan/history', { params })
}

/**
 * 重试扫描任务
 * @param {number} taskId - 任务ID
 * @returns {Promise}
 */
export function retryScanTask(taskId) {
  return request.post(`/scan/tasks/${taskId}/retry`)
}

/**
 * 删除扫描任务
 * @param {number} taskId - 任务ID
 * @returns {Promise}
 */
export function deleteScanTask(taskId) {
  return request.delete(`/scan/tasks/${taskId}`)
}
