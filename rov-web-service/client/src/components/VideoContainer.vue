<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useStreamStore } from '../stores/useStreamStore'
import VideoStream from './VideoStream.vue'

const store = useStreamStore()
const { selected } = storeToRefs(store)

// 根据选中数量决定网格布局（1/2/3/4 自适应）
// 1: 单格
// 2: 左右两格
// 3: 上一下二 或 2x2 留空，这里用 3 格布局（上 1 下 2）
// 4: 2x2
const gridStyle = computed(() => {
    const n = selected.value.length
    switch (n) {
        case 1:
            return {
                'grid-template-columns': '1fr',
                'grid-template-rows': '1fr'
            }
        case 2:
            return {
                'grid-template-columns': '1fr 1fr',
                'grid-template-rows': '1fr'
            }
        case 3:
            // 上方一整行 + 下方两格
            return {
                'grid-template-columns': '1fr 1fr',
                'grid-template-rows': '1fr 1fr'
            }
        case 4:
        default:
            return {
                'grid-template-columns': '1fr 1fr',
                'grid-template-rows': '1fr 1fr'
            }
    }
})

// 3 个流时，让第一项跨满上方两列
function itemSpan(index: number): Record<string, string> {
    if (selected.value.length === 3 && index === 0) {
        return {
            'grid-column': '1 / span 2'
        }
    }
    return {}
}
</script>

<template>
    <div class="video-container">
        <div v-if="selected.length === 0" class="empty-hint">
            <span>请从左侧选择需要显示的视频流</span>
        </div>
        <div v-else class="grid" :style="gridStyle">
            <div
                v-for="(streamId, idx) in selected"
                :key="streamId"
                class="grid-cell"
                :style="itemSpan(idx)"
            >
                <VideoStream :stream-id="streamId" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.video-container {
    width: 100%;
    height: 100%;
    background: #111;
    overflow: hidden;
    display: flex;
}

.grid {
    display: grid;
    width: 100%;
    height: 100%;
    gap: 2px;
    background: #000;
}

.grid-cell {
    width: 100%;
    height: 100%;
    overflow: hidden;
    min-width: 0;
    min-height: 0;
}

.empty-hint {
    margin: auto;
    color: #666;
    font-size: 14px;
}
</style>
