/**
 * 统计管理 API
 */
import request from './request'

/**
 * 获取识别统计信息
 * @returns {Promise}
 */
export function getRecognitionStats() {
  return request.get('/statistics/recognition')
}

/**
 * 获取整理统计信息
 * @returns {Promise}
 */
export function getOrganizeStats() {
  return request.get('/statistics/organize')
}

/**
 * 获取媒体库统计信息
 * @returns {Promise}
 */
export function getMediaStats() {
  return request.get('/statistics/media')
}

/**
 * 获取统计概览
 * @returns {Promise}
 */
export function getStatsOverview() {
  return request.get('/statistics/overview')
}
