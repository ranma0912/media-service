<template>
  <div class="system-management">
    <!-- 进程状态卡片 -->
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <span class="title">服务状态</span>
          <el-button :icon="Refresh" @click="loadProcessStatus">刷新</el-button>
        </div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="运行状态">
          <el-tag :type="processStatus.status === 'running' ? 'success' : 'danger'">
            {{ processStatus.status === 'running' ? '运行中' : '已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进程ID">{{ processStatus.pid || '-' }}</el-descriptions-item>
        <el-descriptions-item label="运行时长">{{ processStatus.uptime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ processStatus.version }}</el-descriptions-item>
        <el-descriptions-item label="启动时间">{{ processStatus.startTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="端口">8000</el-descriptions-item>
      </el-descriptions>
      <div class="process-actions">
        <el-button v-if="processStatus.status !== 'running'" type="success" :icon="VideoPlay" @click="handleStart">启动服务</el-button>
        <el-button v-else type="danger" :icon="VideoPause" @click="handleStop">停止服务</el-button>
        <el-button type="primary" :icon="RefreshRight" @click="handleRestart">重启服务</el-button>
      </div>
    </el-card>

    <!-- 系统资源监控 -->
    <el-row :gutter="24" class="mt-16">
      <el-col :span="8">
        <el-card class="resource-card">
          <template #header>
            <span>CPU使用率</span>
          </template>
          <div ref="cpuChartRef" style="height: 200px;"></div>
          <div class="resource-value">{{ systemStats.cpu }}%</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="resource-card">
          <template #header>
            <span>内存使用率</span>
          </template>
          <div ref="memoryChartRef" style="height: 200px;"></div>
          <div class="resource-value">{{ systemStats.memory }}%</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="resource-card">
          <template #header>
            <span>磁盘使用率</span>
          </template>
          <div ref="diskChartRef" style="height: 200px;"></div>
          <div class="resource-value">{{ systemStats.disk }}%</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 配置管理 -->
    <el-card class="config-card mt-16">
      <template #header>
        <div class="card-header">
          <span class="title">配置管理</span>
        </div>
      </template>
      <el-tabs v-model="activeConfigTab">
        <el-tab-pane label="扫描配置" name="scan">
          <el-form :model="config.scan" label-width="150px">
            <el-form-item>
              <template #label>
                <span>递归扫描</span>
                <el-tooltip content="是否递归扫描子目录" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-switch v-model="config.scan.recursive" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>扫描间隔(秒)</span>
                <el-tooltip content="定期扫描的时间间隔，范围：300-600秒" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input-number v-model="config.scan.interval" :min="300" :max="600" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>监控路径</span>
                <el-tooltip content="需要监控的文件目录路径，每行一个" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-input v-model="config.scan.paths" type="textarea" :rows="3" placeholder="每行一个路径" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig('scan')">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="识别配置" name="recognition">
          <el-form :model="config.recognition" label-width="150px">
            <el-form-item>
              <template #label>
                <span>识别模式</span>
                <el-tooltip content="自动模式：扫描后自动识别；手动模式：需要手动触发识别" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-radio-group v-model="config.recognition.mode">
                <el-radio label="auto">自动</el-radio>
                <el-radio label="manual">手动</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>置信度阈值</span>
                <el-tooltip content="识别结果的可信度阈值，范围：0-100，值越高识别越严格" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-slider v-model="config.recognition.confidence" :min="0" :max="100" />
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>自动整理</span>
                <el-tooltip content="识别成功后是否自动整理文件到目标目录" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-switch v-model="config.recognition.autoOrganize" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig('recognition')">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="整理配置" name="organize">
          <el-form :model="config.organize" label-width="150px">
            <el-form-item>
              <template #label>
                <span>操作类型</span>
                <el-tooltip content="移动：将文件移动到目标目录；复制：复制文件到目标目录；硬链接：创建硬链接到目标目录" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-select v-model="config.organize.actionType">
                <el-option label="移动" value="move" />
                <el-option label="复制" value="copy" />
                <el-option label="硬链接" value="link" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <template #label>
                <span>冲突策略</span>
                <el-tooltip content="跳过：遇到重名文件时跳过；覆盖：覆盖已有文件；重命名：自动重命名新文件" placement="top">
                  <el-icon class="ml-2"><QuestionFilled /></el-icon>
                </el-tooltip>
              </template>
              <el-select v-model="config.organize.conflictStrategy">
                <el-option label="跳过" value="skip" />
                <el-option label="覆盖" value="overwrite" />
                <el-option label="重命名" value="rename" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig('organize')">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { Refresh, VideoPlay, VideoPause, RefreshRight, QuestionFilled } from '@element-plus/icons-vue'

// 进程状态
const processStatus = ref({
  status: 'running',
  pid: 12345,
  uptime: '2天 5小时 30分钟',
  version: '1.0.0',
  startTime: '2024-01-13 06:00:00'
})

// 系统统计
const systemStats = ref({
  cpu: 45,
  memory: 62,
  disk: 75
})

// 历史数据（存储最近60个数据点，每分钟更新一次，共60分钟数据）
const historyData = ref({
  cpu: Array(60).fill(0),
  memory: Array(60).fill(0),
  disk: Array(60).fill(0),
  timestamps: Array(60).fill('')
})

// 图表引用
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const diskChartRef = ref(null)
let cpuChart = null
let memoryChart = null
let diskChart = null

// 配置
const activeConfigTab = ref('scan')
const config = reactive({
  scan: {
    recursive: true,
    interval: 300,
    paths: ''
  },
  recognition: {
    mode: 'auto',
    confidence: 70,
    autoOrganize: false
  },
  organize: {
    actionType: 'move',
    conflictStrategy: 'rename'
  }
})

// 初始化资源监控图表
const initResourceCharts = () => {
  // 生成初始时间戳（每分钟一个）
  const now = new Date()
  for (let i = 59; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 60000)
    historyData.value.timestamps[i] = time.toLocaleTimeString('zh-CN', { hour12: false })
  }

  // CPU折线图配置
  const cpuOption = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>CPU使用率: {c}%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: historyData.value.timestamps,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: 'CPU使用率',
        type: 'line',
        smooth: true,
        data: historyData.value.cpu,
        itemStyle: {
          color: '#67e0e3'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(103, 224, 227, 0.3)' },
              { offset: 1, color: 'rgba(103, 224, 227, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  // 内存折线图配置
  const memoryOption = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>内存使用率: {c}%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: historyData.value.timestamps,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '内存使用率',
        type: 'line',
        smooth: true,
        data: historyData.value.memory,
        itemStyle: {
          color: '#37a2da'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(55, 162, 218, 0.3)' },
              { offset: 1, color: 'rgba(55, 162, 218, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  // 磁盘折线图配置
  const diskOption = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>磁盘使用率: {c}%'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: historyData.value.timestamps,
      axisLabel: {
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [
      {
        name: '磁盘使用率',
        type: 'line',
        smooth: true,
        data: historyData.value.disk,
        itemStyle: {
          color: '#fd666d'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(253, 102, 109, 0.3)' },
              { offset: 1, color: 'rgba(253, 102, 109, 0.05)' }
            ]
          }
        }
      }
    ]
  }

  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value)
    cpuChart.setOption(cpuOption)
  }

  if (memoryChartRef.value) {
    memoryChart = echarts.init(memoryChartRef.value)
    memoryChart.setOption(memoryOption)
  }

  if (diskChartRef.value) {
    diskChart = echarts.init(diskChartRef.value)
    diskChart.setOption(diskOption)
  }
}

// 更新资源监控数据
const updateResourceCharts = () => {
  // 更新历史数据
  historyData.value.cpu.shift()
  historyData.value.cpu.push(systemStats.value.cpu)

  historyData.value.memory.shift()
  historyData.value.memory.push(systemStats.value.memory)

  historyData.value.disk.shift()
  historyData.value.disk.push(systemStats.value.disk)

  // 更新时间戳
  historyData.value.timestamps.shift()
  historyData.value.timestamps.push(new Date().toLocaleTimeString('zh-CN', { hour12: false }))

  // 更新图表
  if (cpuChart) {
    cpuChart.setOption({
      xAxis: { data: historyData.value.timestamps },
      series: [{ data: historyData.value.cpu }]
    })
  }
  if (memoryChart) {
    memoryChart.setOption({
      xAxis: { data: historyData.value.timestamps },
      series: [{ data: historyData.value.memory }]
    })
  }
  if (diskChart) {
    diskChart.setOption({
      xAxis: { data: historyData.value.timestamps },
      series: [{ data: historyData.value.disk }]
    })
  }
}

// 加载进程状态
const loadProcessStatus = async () => {
  try {
    // 调用实际API
    const { getProcessStatus } = await import('@/api/process')
    const res = await getProcessStatus()
    processStatus.value = {
      status: res.status || 'unknown',
      pid: res.pid || null,
      uptime: res.uptime || '-',
      version: res.version || '1.0.0',
      startTime: res.start_time || '-'
    }
  } catch (error) {
    console.error('加载进程状态失败:', error)
    ElMessage.error('加载进程状态失败')
  }
}

// 启动服务
const handleStart = async () => {
  try {
    await ElMessageBox.confirm('确定要启动服务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })

    // 调用实际API
    const { startService } = await import('@/api/process')
    await startService()

    ElMessage.success('服务启动成功')
    loadProcessStatus()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('启动服务失败:', error)
      ElMessage.error('启动服务失败')
    }
  }
}

// 停止服务
const handleStop = async () => {
  try {
    await ElMessageBox.confirm('确定要停止服务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用实际API
    const { stopService } = await import('@/api/process')
    await stopService()

    ElMessage.success('服务停止成功')
    loadProcessStatus()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止服务失败:', error)
      ElMessage.error('停止服务失败')
    }
  }
}

// 重启服务
const handleRestart = async () => {
  try {
    await ElMessageBox.confirm('确定要重启服务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用实际API
    const { restartService } = await import('@/api/process')
    await restartService()

    ElMessage.success('服务重启成功')
    loadProcessStatus()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重启服务失败:', error)
      ElMessage.error('重启服务失败')
    }
  }
}

// 保存配置
const handleSaveConfig = async (type) => {
  try {
    // 调用实际API
    const { updateConfigValue } = await import('@/api/config')

    // 根据类型保存不同的配置
    if (type === 'scan') {
      await updateConfigValue('scan.recursive', config.scan.recursive)
      await updateConfigValue('scan.interval', config.scan.interval)
      await updateConfigValue('scan.paths', config.scan.paths.split('\n'))
    } else if (type === 'recognition') {
      await updateConfigValue('recognition.mode', config.recognition.mode)
      await updateConfigValue('recognition.confidence', config.recognition.confidence / 100)
      await updateConfigValue('recognition.autoOrganize', config.recognition.autoOrganize)
    } else if (type === 'organize') {
      await updateConfigValue('organize.actionType', config.organize.actionType)
      await updateConfigValue('organize.conflictStrategy', config.organize.conflictStrategy)
    }

    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败')
  }
}

// 窗口大小改变时重绘图表
const handleResize = () => {
  cpuChart?.resize()
  memoryChart?.resize()
  diskChart?.resize()
}

// 定时更新系统资源
let resourceTimer = null
const loadSystemStats = async () => {
  try {
    const { getSystemStats } = await import('@/api/process')
    const res = await getSystemStats()
    systemStats.value = {
      cpu: res.cpu,
      memory: res.memory,
      disk: res.disk
    }
    updateResourceCharts()
  } catch (error) {
    console.error('加载系统资源统计失败:', error)
  }
}

const startResourceMonitor = () => {
  resourceTimer = setInterval(() => {
    loadSystemStats()
  }, 60000)
}

onMounted(() => {
  loadProcessStatus()
  initResourceCharts()
  updateResourceCharts()
  startResourceMonitor()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cpuChart?.dispose()
  memoryChart?.dispose()
  diskChart?.dispose()
  if (resourceTimer) {
    clearInterval(resourceTimer)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.system-management {
  .status-card {
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: 16px;
        font-weight: 500;
      }
    }

    .process-actions {
      margin-top: 16px;
      display: flex;
      gap: 12px;
    }
  }

  .resource-card {
    .resource-value {
      text-align: center;
      font-size: 24px;
      font-weight: bold;
      color: #333;
      margin-top: -20px;
    }
  }

  .config-card {
    .card-header {
      .title {
        font-size: 16px;
        font-weight: 500;
      }
    }
  }
}
</style>
