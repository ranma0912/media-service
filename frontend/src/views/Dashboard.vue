<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="24">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #1890ff;">
              <el-icon><VideoPlay /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalFiles }}</div>
              <div class="stat-label">媒体文件总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #52c41a;">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.recognizedFiles }}</div>
              <div class="stat-label">已识别文件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #faad14;">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pendingFiles }}</div>
              <div class="stat-label">待识别文件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #722ed1;">
              <el-icon><Folder /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatSize(stats.totalSize) }}</div>
              <div class="stat-label">媒体库总容量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="24" class="mt-16">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>媒体类型分布</span>
          </template>
          <div ref="typeChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <span>质量分布</span>
          </template>
          <div ref="qualityChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-card class="mt-16">
      <template #header>
        <span>快捷操作</span>
      </template>
      <div class="quick-actions">
        <el-button type="primary" :icon="VideoCamera" @click="handleScan">
          立即扫描
        </el-button>
        <el-button type="success" :icon="Collection" @click="handleRecognition">
          查看待识别
        </el-button>
        <el-button type="warning" :icon="FolderOpened" @click="handleOrganize">
          查看待整理
        </el-button>
        <el-button :icon="Setting" @click="handleSettings">
          系统设置
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { VideoPlay, CircleCheck, Clock, Folder, VideoCamera, Collection, FolderOpened, Setting } from '@element-plus/icons-vue'

const router = useRouter()

// 统计数据
const stats = ref({
  totalFiles: 0,
  recognizedFiles: 0,
  pendingFiles: 0,
  totalSize: 0
})

// 图表引用
const typeChartRef = ref(null)
const qualityChartRef = ref(null)
let typeChart = null
let qualityChart = null

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 初始化类型分布图表
const initTypeChart = () => {
  if (!typeChartRef.value) return

  typeChart = echarts.init(typeChartRef.value)
  typeChart.setOption({
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '媒体类型',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 1048, name: '电影' },
          { value: 735, name: '剧集' },
          { value: 580, name: '动漫' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  })
}

// 初始化质量分布图表
const initQualityChart = () => {
  if (!qualityChartRef.value) return

  qualityChart = echarts.init(qualityChartRef.value)
  qualityChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: ['720p', '1080p', '4K']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '文件数',
        type: 'bar',
        data: [120, 200, 150],
        itemStyle: {
          color: '#1890ff'
        }
      }
    ]
  })
}

// 快捷操作
const handleScan = () => {
  router.push('/scan')
}

const handleRecognition = () => {
  router.push('/recognition')
}

const handleOrganize = () => {
  router.push('/organize')
}

const handleSettings = () => {
  router.push('/system')
}

// 加载统计数据
const loadStats = async () => {
  try {
    // 调用实际API获取媒体统计
    const { getMediaStats } = await import('@/api/media')
    const mediaStats = await getMediaStats()

    stats.value.totalFiles = mediaStats.total_files || 0
    stats.value.totalSize = mediaStats.total_size || 0

    // 从识别统计API获取已识别和待识别文件数
    const { getRecognitionStats } = await import('@/api/statistics')
    const recognitionStats = await getRecognitionStats()
    stats.value.recognizedFiles = recognitionStats.success || 0
    stats.value.pendingFiles = recognitionStats.total || 0

    // 更新类型分布图表
    if (typeChart && mediaStats.type_distribution) {
      const typeData = Object.entries(mediaStats.type_distribution).map(([key, value]) => ({
        value,
        name: key === 'movie' ? '电影' : key === 'tv' ? '剧集' : key === 'anime' ? '动漫' : '其他'
      }))
      typeChart.setOption({
        series: [{
          data: typeData
        }]
      })
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

// 窗口大小改变时重绘图表
const handleResize = () => {
  typeChart?.resize()
  qualityChart?.resize()
}

onMounted(() => {
  loadStats()
  initTypeChart()
  initQualityChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  typeChart?.dispose()
  qualityChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;

      .stat-icon {
        width: 60px;
        height: 60px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 16px;

        .el-icon {
          font-size: 32px;
          color: #fff;
        }
      }

      .stat-info {
        flex: 1;

        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #333;
          margin-bottom: 8px;
        }

        .stat-label {
          font-size: 14px;
          color: #666;
        }
      }
    }
  }

  .chart-card {
    :deep(.el-card__header) {
      padding: 16px;
      font-weight: 500;
    }
  }

  .quick-actions {
    display: flex;
    gap: 16px;
  }
}
</style>
