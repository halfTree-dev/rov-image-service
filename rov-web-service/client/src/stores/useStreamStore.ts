import { defineStore } from 'pinia'

// 最大同时显示的视频流数量
export const MAX_SELECTED = 4

// 视频流状态管理
export const useStreamStore = defineStore('stream', {
    state: () => ({
        // 已发现的视频流列表
        streams: [] as string[],
        // 当前选中的视频流（数组便于响应式）
        selected: [] as string[]
    }),
    getters: {
        // 选中的数量
        selectedCount: (state) => state.selected.length,
        // 是否已达选中上限
        isMaxSelected: (state) => state.selected.length >= MAX_SELECTED,
        // 判断流是否被选中
        isSelected: (state) => (streamId: string) => state.selected.includes(streamId)
    },
    actions: {
        // 注册一个新发现的流（去重）
        registerStream(streamId: string) {
            if (!this.streams.includes(streamId)) {
                this.streams.push(streamId)
            }
        },

        // 切换某个流的选中状态
        toggleSelect(streamId: string): boolean {
            const idx = this.selected.indexOf(streamId)
            if (idx >= 0) {
                // 已选中，取消选中
                this.selected.splice(idx, 1)
                return true
            }

            // 未选中，添加选中（受上限约束）
            if (this.selected.length >= MAX_SELECTED) {
                return false
            }
            this.selected.push(streamId)
            return true
        },

        // 清空选中
        clearSelection() {
            this.selected.splice(0, this.selected.length)
        }
    }
})
