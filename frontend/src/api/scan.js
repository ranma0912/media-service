/**
 * 扫描管理 API
 */
import request from './request'

// ========== 扫描触发 ==========

/**
 * 手动触发扫描
 * @param {Object} data - 任务数据
 * @param {string} data.path - 扫描路径
 * @param {boolean} data.use_default_strategy - 是否使用默认扫描策略
 * @param {string} data.scan_type - 扫描类型 (full/incremental/custom/rescan) - use_default_strategy=false时必填
 * @param {boolean} data.recursive - 是否递归扫描 - use_default_strategy=false时必填
 * @param {string} data.skip_strategy - 文件跳过模式 (keyword/keyword_or_scanned/none) - use_default_strategy=false时必填
 * @returns {Promise}
 */
export function createScanTask(data) {
  return request.post('/scan/trigger', data)
}



// ========== 扫描路径 ==========

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
 * @param {string} data.path_name - 路径名称
 * @param {string} data.path - 路径
 * @param {string} data.scan_type - 扫描类型 (full/incremental)
 * @param {boolean} data.recursive - 是否递归
 * @param {string} data.skip_mode - 跳过模式 (keyword/record/none)
 * @param {boolean} data.skip_subdirs - 是否跳过子目录
 * @param {number} data.monitor_debounce_time - 监控防抖时间（秒）
 * @param {boolean} data.monitoring_enabled - 是否启用监控
 * @param {string} data.monitor_mode - 监控模式
 * @param {number} data.monitor_debounce - 监控防抖时间（秒）
 * @param {boolean} data.auto_recognize - 是否自动识别
 * @param {boolean} data.auto_organize - 是否自动整理
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
 * //   default_monitor_debounce_time: 30
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
 * @param {number} config.default_monitor_debounce_time - 默认监控防抖时间（30-300秒）
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

// ========== 文件任务管理 ==========

/**
 * 获取文件任务列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.status - 任务状态
 * @param {string} params.path_id - 路径ID
 * @param {string} params.search - 搜索关键词
 * @returns {Promise}
 */
export function getFileTasks(params) {
  return request.get('/scan/file-tasks', { params })
}

/**
 * 获取文件任务详情
 * @param {number} taskId - 文件任务ID
 * @returns {Promise}
 */
export function getFileTask(taskId) {
  return request.get(`/scan/file-tasks/${taskId}`)
}

/**
 * 查看扫描结果详情
 * @param {number} taskId - 文件任务ID
 * @returns {Promise}
 */
export function getScanResult(taskId) {
  return request.get(`/scan/file-tasks/${taskId}`)
}

/**
 * 重新扫描文件
 * @param {number} taskId - 文件任务ID
 * @returns {Promise}
 */
export function rescanFile(taskId) {
  return request.post(`/scan/file-tasks/${taskId}/rescan`)
}

/**
 * 停止扫描文件
 * @param {number} taskId - 文件任务ID
 * @returns {Promise}
 */
export function stopFileScan(taskId) {
  return request.post(`/scan/file-tasks/${taskId}/stop`)
}

/**
 * 删除扫描结果
 * @param {number} taskId - 文件任务ID
 * @returns {Promise}
 */
export function deleteScanResult(taskId) {
  return request.delete(`/scan/file-tasks/${taskId}`)
}


/**
 * ========== 基于媒体文件ID的操作 ========== */

/**
 * 重新扫描媒体文件（基于media_file_id）
 * @param {number} mediaFileId - 媒体文件ID
 * @returns {Promise}
 */
export function rescanMediaFile(mediaFileId) {
  return request.post(`/scan/files/${mediaFileId}/rescan`)
}

/**
 * 停止扫描媒体文件（基于media_file_id）
 * @param {number} mediaFileId - 媒体文件ID
 * @returns {Promise}
 */
export function stopMediaFileScan(mediaFileId) {
  return request.post(`/scan/files/${mediaFileId}/stop`)
}

/**
 * 删除媒体文件扫描结果（基于media_file_id）
 * @param {number} mediaFileId - 媒体文件ID
 * @returns {Promise}
 */
export function deleteMediaFileScanResult(mediaFileId) {
  return request.delete(`/scan/files/${mediaFileId}`)
}

/**
 * 批量重新扫描媒体文件（基于media_file_id）
 * @param {Array<number>} mediaFileIds - 媒体文件ID列表
 * @returns {Promise}
 */
export function batchRescanMediaFiles(mediaFileIds) {
  return request.post('/scan/files/batch/rescan', { media_file_ids: mediaFileIds })
}

/**
 * 批量停止扫描媒体文件（基于media_file_id）
 * @param {Array<number>} mediaFileIds - 媒体文件ID列表
 * @returns {Promise}
 */
export function batchStopMediaFileScans(mediaFileIds) {
  return request.post('/scan/files/batch/stop', { media_file_ids: mediaFileIds })
}

/**
 * 批量删除媒体文件扫描结果（基于media_file_id）
 * @param {Array<number>} mediaFileIds - 媒体文件ID列表
 * @returns {Promise}
 */
export function batchDeleteMediaFileScanResults(mediaFileIds) {
  return request.delete('/scan/files/batch', { data: { media_file_ids: mediaFileIds } })
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