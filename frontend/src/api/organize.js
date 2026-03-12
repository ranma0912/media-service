
/**
 * 整理管理 API
 */
import request from './request'

/**
 * 获取整理任务列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.status - 任务状态
 * @returns {Promise}
 */
export function getOrganizeTasks(params) {
  return request.get('/organize/tasks', { params })
}

/**
 * 获取整理任务详情
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function getOrganizeTask(taskId) {
  return request.get(`/organize/tasks/${taskId}`)
}

/**
 * 创建整理任务
 * @param {Object} data - 任务数据
 * @param {Array<number>} data.file_ids - 文件ID列表
 * @param {string} data.action_type - 操作类型 (move/copy/link)
 * @param {string} data.conflict_strategy - 冲突策略 (skip/overwrite/rename)
 * @returns {Promise}
 */
export function createOrganizeTask(data) {
  return request.post('/organize/tasks', data)
}

/**
 * 停止整理任务
 * @param {string} taskId - 任务ID
 * @returns {Promise}
 */
export function stopOrganizeTask(taskId) {
  return request.post(`/organize/tasks/${taskId}/stop`)
}

/**
 * 预览整理结果
 * @param {number} fileId - 文件ID
 * @param {Object} data - 整理数据
 * @returns {Promise}
 */
export function previewOrganize(fileId, data) {
  return request.post(`/organize/files/${fileId}/preview`, data)
}

/**
 * 获取整理统计
 * @returns {Promise}
 */
export function getOrganizeStats() {
  return request.get('/organize/stats')
}

/**
 * 获取命名规则
 * @returns {Promise}
 */
export function getNamingRules() {
  return request.get('/config/naming-rules')
}

/**
 * 更新命名规则
 * @param {Object} data - 规则数据
 * @returns {Promise}
 */
export function updateNamingRules(data) {
  return request.put('/config/naming-rules', data)
}
