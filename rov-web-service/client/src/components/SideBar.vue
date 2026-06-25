<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useStreamStore, MAX_SELECTED } from '../stores/useStreamStore'
import { videoService } from '../services/video'

const store = useStreamStore()
const { streams, selected } = storeToRefs(store)

let unsubStream: (() => void) | null = null

onMounted(() => {
    // 连接视频流并监听新流发现
    videoService.connect()
    unsubStream = videoService.onStreamDiscovered((streamId) => {
        store.registerStream(streamId)
    })

    // 预加载已知流（重连后可能已知）
    for (const s of videoService.getKnownStreams()) {
        store.registerStream(s)
    }
})

onUnmounted(() => {
    if (unsubStream) {
        unsubStream()
    }
})

function onItemClick(streamId: string) {
    // 切换选中；若达到上限且新增失败则提示
    const ok = store.toggleSelect(streamId)
    if (!ok) {
        alert(`最多同时显示 ${MAX_SELECTED} 个视频流`)
    }
}

function isSelected(streamId: string): boolean {
    return selected.value.includes(streamId)
}
</script>

<template>
    <div class="sidebar-panel">
        <div class="sidebar-header">
            <span>视频流</span>
            <span class="counter">{{ selected.length }}/{{ MAX_SELECTED }}</span>
        </div>
        <ul class="stream-list">
            <li
                v-for="stream in streams"
                :key="stream"
                class="stream-item"
                :class="{ active: isSelected(stream) }"
                @click="onItemClick(stream)"
            >
                <span class="dot" :class="{ live: isSelected(stream) }"></span>
                <span class="name">{{ stream }}</span>
            </li>
            <li v-if="streams.length === 0" class="empty">等待视频流接入...</li>
        </ul>
    </div>
</template>

<style scoped>
.sidebar-panel {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #1e1e1e;
    color: #e0e0e0;
}

.sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    font-size: 14px;
    font-weight: 600;
    border-bottom: 1px solid #333;
}

.counter {
    font-size: 12px;
    color: #888;
    font-weight: 400;
}

.stream-list {
    list-style: none;
    margin: 0;
    padding: 6px 0;
    overflow-y: auto;
    flex: 1;
}

.stream-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    cursor: pointer;
    user-select: none;
    transition: background 0.15s;
}

.stream-item:hover {
    background: #2a2a2a;
}

.stream-item.active {
    background: #2d4f7a;
    color: #fff;
}

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #555;
}

.dot.live {
    background: #ff4d4f;
    box-shadow: 0 0 6px #ff4d4f;
}

.name {
    font-size: 13px;
}

.empty {
    list-style: none;
    padding: 16px 14px;
    color: #666;
    font-size: 12px;
    text-align: center;
}
</style>
