
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

/**
 * 批量停止扫描任务
 * @param {Array<number>} taskIds - 任务ID列表
 * @returns {Promise}
 */
export function batchStopTasks(taskIds) {
  return request.post('/scan/tasks/batch/stop', { task_ids: taskIds })
}

/**
 * 批量删除扫描任务
 * @param {Array<number>} taskIds - 任务ID列表
 * @returns {Promise}
 */
export function batchDeleteTasks(taskIds) {
  return request.delete('/scan/tasks/batch', { data: { task_ids: taskIds } })
}

/**
 * 浏览目录
 * @param {string} path - 要浏览的目录路径
 * @returns {Promise}
 */
export function browseDirectory(path) {
  return request.get('/scan/browse', { params: { path } })
}

// ========== 默认扫描策略 ==========

/**
 * 获取默认扫描策略配置
 * @returns {Promise}
 * @example
 * // 返回数据示例：
 * // {
 * //   default_scan_type: "full",
 * //   default_recursive: true,
 * //   default_skip_mode: "keyword",
 * //   default_ignore_patterns: []
 * // }
 */
export function getDefaultScanConfig() {
  return request.get('/scan/config/default')
}

/**
 * 更新默认扫描策略配置
 * @param {Object} config - 配置对象
 * @param {string} config.default_scan_type - 默认扫描类型 (full/incremental)
 * @param {boolean} config.default_recursive - 默认递归扫描
 * @param {string} config.default_skip_mode - 默认文件跳过模式 (keyword/record/none)
 * @param {Array<string>} config.default_ignore_patterns - 默认忽略文件模式列表
 * @returns {Promise}
 */
export function updateDefaultScanConfig(config) {
  return request.put('/scan/config/default', config)
}

/**
 * 重置默认扫描策略
 * @returns {Promise}
 */
export function resetDefaultScanConfig() {
  return request.post('/scan/config/default/reset')
}

// ========== 文件系统监控 ==========

/**
 * 启动文件监控
 * @param {number} pathId - 扫描路径ID
 * @returns {Promise}
 */
export function startMonitoring(pathId) {
  return request.post(`/scan/monitoring/${pathId}/start`)
}

/**
 * 停止文件监控
 * @param {number} pathId - 扫描路径ID
 * @returns {Promise}
 */
export function stopMonitoring(pathId) {
  return request.post(`/scan/monitoring/${pathId}/stop`)
}

/**
 * 获取文件监控状态
 * @param {number} pathId - 扫描路径ID
 * @returns {Promise}
 */
export function getMonitoringStatus(pathId) {
  return request.get(`/scan/monitoring/${pathId}/status`)
}

/**
 * 获取所有路径的监控状态
 * @returns {Promise}
 */
export function listMonitoringStatus() {
  return request.get('/scan/monitoring')
}

// ========== 扫描任务调度器 ==========

/**
 * 获取调度器状态
 * @returns {Promise}
 */
export function getSchedulerStatus() {
  return request.get('/scan/scheduler/status')
}

/**
 * 启动调度器
 * @returns {Promise}
 */
export function startScheduler() {
  return request.post('/scan/scheduler/start')
}

/**
 * 停止调度器
 * @returns {Promise}
 */
export function stopScheduler() {
  return request.post('/scan/scheduler/stop')
}

/**
 * 获取指定路径的定时任务状态
 * @param {number} pathId - 扫描路径ID
 * @returns {Promise}
 */
export function getScheduledJob(pathId) {
  return request.get(`/scan/scheduler/jobs/${pathId}`)
}
