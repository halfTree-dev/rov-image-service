<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { videoService, type VideoFrame } from '../services/video'

const props = defineProps<{
    streamId: string
}>()

const imgSrc = ref<string>('')
let unsubFrame: (() => void) | null = null
let currentUrl: string | null = null

onMounted(() => {
    // onFrame 是 video.ts 留出的回调接口
    // 此处将 renderFrame 包装为 lambda 函数传入，这样 video 触发接受帧时，就会顺带执行此处的渲染
    unsubFrame = videoService.onFrame(props.streamId, (frame: VideoFrame) => {
        renderFrame(frame)
    })
})

onBeforeUnmount(() => {
    if (unsubFrame) {
        unsubFrame()
    }
    revokeUrl()
})

// 将一帧 JPEG 渲染为 <img>
function renderFrame(frame: VideoFrame) {
    const blob = new Blob([frame.jpeg], { type: 'image/jpeg' })
    const url = URL.createObjectURL(blob)

    // 释放上一帧的 URL，避免内存泄漏
    const prev = currentUrl
    imgSrc.value = url
    currentUrl = url

    if (prev) {
        URL.revokeObjectURL(prev)
    }

    console.log(frame.timestamp);
}

function revokeUrl() {
    if (currentUrl) {
        URL.revokeObjectURL(currentUrl)
        currentUrl = null
        imgSrc.value = ''
    }
}
</script>

<template>
    <!-- 该 VideoStream 实际上为一 img 构件，接受传入的 JPEG 数据 -->
    <div class="video-stream">
        <img
            v-if="imgSrc"
            class="frame"
            :src="imgSrc"
            alt="video"
        />
        <div v-else class="placeholder">
            <span>等待 {{ streamId }} 帧数据...</span>
        </div>
        <div class="label">{{ streamId }}</div>
    </div>
</template>

<style scoped>
.video-stream {
    position: relative;
    width: 100%;
    height: 100%;
    background: #000;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.frame {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.placeholder {
    color: #666;
    font-size: 13px;
}

.label {
    position: absolute;
    top: 6px;
    left: 8px;
    padding: 2px 8px;
    font-size: 12px;
    color: #fff;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 3px;
    pointer-events: none;
}
</style>
