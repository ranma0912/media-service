
/**
 * 识别管理 API
 */
import request from './request'

/**
 * 获取识别任务列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.status - 任务状态
 * @returns {Promise}
 */
export function getRecognitionTasks(params) {
  return request.get('/recognition/tasks', { params })
}

/**
 * 获取识别任务详情
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function getRecognitionTask(taskId) {
  return request.get(`/recognition/tasks/${taskId}`)
}

/**
 * 创建识别任务
 * @param {Object} data - 任务数据
 * @param {Array<number>} data.file_ids - 文件ID列表
 * @returns {Promise}
 */
export function createRecognitionTask(data) {
  return request.post('/recognition/tasks', data)
}

/**
 * 停止识别任务
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function stopRecognitionTask(taskId) {
  return request.post(`/recognition/tasks/${taskId}/stop`)
}

/**
 * 搜索媒体信息
 * @param {Object} params - 搜索参数
 * @param {string} params.keyword - 关键词
 * @param {string} params.media_type - 媒体类型
 * @param {string} params.tmdb_id - TMDB ID
 * @returns {Promise}
 */
export function searchMedia(params) {
  return request.get('/recognition/search', { params })
}

/**
 * 手动指定识别结果
 * @param {number} fileId - 文件ID
 * @param {Object} data - 识别数据
 * @returns {Promise}
 */
export function manualRecognize(fileId, data) {
  return request.post(`/recognition/files/${fileId}/manual`, data)
}

/**
 * 获取识别统计
 * @returns {Promise}
 */
export function getRecognitionStats() {
  return request.get('/recognition/stats')
}
