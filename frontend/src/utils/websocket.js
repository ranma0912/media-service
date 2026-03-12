
/**
 * WebSocket客户端工具类
 */
class WebSocketClient {
  constructor(url) {
    this.url = url
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectInterval = 5000 // 5秒
    this.listeners = new Map()
    this.shouldReconnect = true
    this.connect()
  }

  /**
   * 连接WebSocket
   */
  connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket连接成功:', this.url)
        this.reconnectAttempts = 0
        this.emit('connected')
      }

      this.ws.onclose = () => {
        console.log('WebSocket连接关闭:', this.url)
        this.emit('disconnected')

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)
          setTimeout(() => this.connect(), this.reconnectInterval)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
        this.emit('error', error)
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.emit('message', data)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      }
    } catch (error) {
      console.error('创建WebSocket连接失败:', error)
      this.emit('error', error)
    }
  }

  /**
   * 发送消息
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  /**
   * 发送心跳
   */
  sendHeartbeat() {
    this.send({ type: 'heartbeat', timestamp: Date.now() })
  }

  /**
   * 关闭连接
   */
  close() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
    }
  }

  /**
   * 添加事件监听器
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  }

  /**
   * 移除事件监听器
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event)
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data))
    }
  }

  /**
   * 获取连接状态
   */
  getReadyState() {
    if (!this.ws) return 'DISCONNECTED'

    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING'
      case WebSocket.OPEN:
        return 'CONNECTED'
      case WebSocket.CLOSING:
        return 'CLOSING'
      case WebSocket.CLOSED:
        return 'CLOSED'
      default:
        return 'UNKNOWN'
    }
  }

  /**
   * 是否已连接
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN
  }
}

export default WebSocketClient
