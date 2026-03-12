
/**
 * 配置管理 API
 */
import request from './request'

/**
 * 获取完整配置
 * @returns {Promise}
 */
export function getConfig() {
  return request.get('/config')
}

/**
 * 获取单个配置项
 * @param {string} key - 配置键
 * @returns {Promise}
 */
export function getConfigValue(key) {
  return request.get(`/config/${key}`)
}

/**
 * 更新配置项
 * @param {string} key - 配置键
 * @param {any} value - 配置值
 * @returns {Promise}
 */
export function updateConfigValue(key, value) {
  return request.put(`/config/${key}`, { key, value })
}

/**
 * 重新加载配置
 * @returns {Promise}
 */
export function reloadConfig() {
  return request.post('/config/reload')
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
