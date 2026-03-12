
/**
 * 媒体管理 API
 */
import request from './request'

/**
 * 获取媒体文件列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @param {string} params.media_type - 媒体类型
 * @param {string} params.search - 搜索关键词
 * @returns {Promise}
 */
export function getMediaFiles(params) {
  return request.get('/media/files', { params })
}

/**
 * 获取媒体文件详情
 * @param {number} id - 文件ID
 * @returns {Promise}
 */
export function getMediaFile(id) {
  return request.get(`/media/files/${id}`)
}

/**
 * 删除媒体文件记录
 * @param {number} id - 文件ID
 * @returns {Promise}
 */
export function deleteMediaFile(id) {
  return request.delete(`/media/files/${id}`)
}

/**
 * 获取媒体库统计信息
 * @returns {Promise}
 */
export function getMediaStats() {
  return request.get('/media/stats')
}
