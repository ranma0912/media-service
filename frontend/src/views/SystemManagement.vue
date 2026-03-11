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
            <el-form-item label="递归扫描">
              <el-switch v-model="config.scan.recursive" />
            </el-form-item>
            <el-form-item label="扫描间隔(秒)">
              <el-input-number v-model="config.scan.interval" :min="60" :max="3600" />
            </el-form-item>
            <el-form-item label="监控路径">
              <el-input v-model="config.scan.paths" type="textarea" :rows="3" placeholder="每行一个路径" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig('scan')">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="识别配置" name="recognition">
          <el-form :model="config.recognition" label-width="150px">
            <el-form-item label="识别模式">
              <el-radio-group v-model="config.recognition.mode">
                <el-radio label="auto">自动</el-radio>
                <el-radio label="manual">手动</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="置信度阈值">
              <el-slider v-model="config.recognition.confidence" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="自动整理">
              <el-switch v-model="config.recognition.autoOrganize" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveConfig('recognition')">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="整理配置" name="organize">
          <el-form :model="config.organize" label-width="150px">
            <el-form-item label="操作类型">
              <el-select v-model="config.organize.actionType">
                <el-option label="移动" value="move" />
                <el-option label="复制" value="copy" />
                <el-option label="硬链接" value="link" />
              </el-select>
            </el-form-item>
            <el-form-item label="冲突策略">
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
import { Refresh, VideoPlay, VideoPause, RefreshRight } from '@element-plus/icons-vue'

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
    paths: 'D:/Downloads\nE:/Media/Inbox'
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
  const chartOptions = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 10,
            color: [
              [0.6, '#67e0e3'],
              [0.8, '#37a2da'],
              [1, '#fd666d']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z M12.8,0.7L0.2,40.1h25.3L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 20,
          distance: -60,
          formatter: '{value}%'
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 30
        },
        detail: {
          fontSize: 60,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: '{value}%',
          color: 'auto'
        },
        data: [
          {
            value: 0
          }
        ]
      }
    ]
  }

  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value)
    cpuChart.setOption(chartOptions)
  }

  if (memoryChartRef.value) {
    memoryChart = echarts.init(memoryChartRef.value)
    memoryChart.setOption(chartOptions)
  }

  if (diskChartRef.value) {
    diskChart = echarts.init(diskChartRef.value)
    diskChart.setOption(chartOptions)
  }
}

// 更新资源监控数据
const updateResourceCharts = () => {
  if (cpuChart) {
    cpuChart.setOption({
      series: [{ data: [{ value: systemStats.value.cpu }] }]
    })
  }
  if (memoryChart) {
    memoryChart.setOption({
      series: [{ data: [{ value: systemStats.value.memory }] }]
    })
  }
  if (diskChart) {
    diskChart.setOption({
      series: [{ data: [{ value: systemStats.value.disk }] }]
    })
  }
}

// 加载进程状态
const loadProcessStatus = async () => {
  try {
    // TODO: 调用实际API
    // const res = await request.get('/api/process/status')
    // processStatus.value = res.data
  } catch (error) {
    ElMessage.error('加载进程状态失败')
  }
}

// 启动服务
const handleStart = () => {
  ElMessageBox.confirm('确定要启动服务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    try {
      // TODO: 调用实际API
      // await request.post('/api/process/control', { action: 'start' })
      ElMessage.success('服务启动成功')
      loadProcessStatus()
    } catch (error) {
      ElMessage.error('启动服务失败')
    }
  }).catch(() => {})
}

// 停止服务
const handleStop = () => {
  ElMessageBox.confirm('确定要停止服务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      // TODO: 调用实际API
      // await request.post('/api/process/control', { action: 'stop' })
      ElMessage.success('服务停止成功')
      loadProcessStatus()
    } catch (error) {
      ElMessage.error('停止服务失败')
    }
  }).catch(() => {})
}

// 重启服务
const handleRestart = () => {
  ElMessageBox.confirm('确定要重启服务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      // TODO: 调用实际API
      // await request.post('/api/process/control', { action: 'restart' })
      ElMessage.success('服务重启成功')
      loadProcessStatus()
    } catch (error) {
      ElMessage.error('重启服务失败')
    }
  }).catch(() => {})
}

// 保存配置
const handleSaveConfig = async (type) => {
  try {
    // TODO: 调用实际API
    // await request.put(`/api/config/${type}`, config[type])
    ElMessage.success('配置保存成功')
  } catch (error) {
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
const startResourceMonitor = () => {
  resourceTimer = setInterval(() => {
    // TODO: 调用实际API获取系统资源数据
    // 模拟数据变化
    systemStats.value = {
      cpu: Math.floor(Math.random() * 40) + 30,
      memory: Math.floor(Math.random() * 20) + 55,
      disk: 75
    }
    updateResourceCharts()
  }, 5000)
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
