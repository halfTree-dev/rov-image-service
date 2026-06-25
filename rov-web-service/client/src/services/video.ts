// 视频流 WebSocket 客户端
// 协议 [4 字节大端 headerLength][headerLength 字节 JSON 头][JPEG body]
// JSON 头：{ streamId: string, timestamp: number }

export interface VideoFrame {
    streamId: string
    timestamp: number
    jpeg: ArrayBuffer
}

type FrameHandler = (frame: VideoFrame) => void
type StreamHandler = (streamId: string) => void

// 单例视频流服务
class VideoService {
    private socket: WebSocket | null = null
    private readonly frameHandlers: Map<string, Set<FrameHandler>> = new Map()
    private readonly streamHandlers: Set<StreamHandler> = new Set()
    private readonly knownStreams: Set<string> = new Set()
    private reconnectTimer: number | null = null

    // 连接 WebSocket，自动重连
    public connect(): void {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            return
        }

        // 此处在生产环境需指向实际后端
        const url = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws/video`
        const socket = new WebSocket(url)
        socket.binaryType = 'arraybuffer'

        socket.onopen = () => {
            console.log('[VideoService] WS 已连接')
        }

        // video.ts 主持 socket 服务
        // 当接受到新的帧消息时，投入帧到 handleMessage() 处理
        socket.onmessage = (event: MessageEvent) => {
            this.handleMessage(event)
        }

        socket.onclose = () => {
            console.log('[VideoService] WS 断开，1.5s 后重连')
            this.scheduleReconnect()
        }

        socket.onerror = () => {
            // close 事件会随后触发并调度重连
        }

        this.socket = socket
    }

    // 订阅某个流的新帧，传入的 handler 将在新帧到达时被调用
    public onFrame(streamId: string, handler: FrameHandler): () => void {
        let set = this.frameHandlers.get(streamId)
        if (!set) {
            set = new Set()
            this.frameHandlers.set(streamId, set)
        }
        set.add(handler)
        return () => {
            set!.delete(handler)
        }
    }

    // 订阅新发现的流（用于侧边栏更新）
    public onStreamDiscovered(handler: StreamHandler): () => void {
        this.streamHandlers.add(handler)
        return () => {
            this.streamHandlers.delete(handler)
        }
    }

    // 当前已知的流名列表
    public getKnownStreams(): string[] {
        return Array.from(this.knownStreams)
    }

    private scheduleReconnect(): void {
        if (this.reconnectTimer !== null) {
            return
        }
        this.reconnectTimer = window.setTimeout(() => {
            this.reconnectTimer = null
            this.socket = null
            this.connect()
        }, 1500)
    }

    private handleMessage(event: MessageEvent): void {
        if (!(event.data instanceof ArrayBuffer)) {
            return
        }

        const frame = this.parseFrame(event.data)
        if (!frame) {
            return
        }

        // 发现新流时通知订阅者
        if (!this.isKnownStream(frame.streamId)) {
            this.knownStreams.add(frame.streamId)
            for (const h of this.streamHandlers) {
                try {
                    h(frame.streamId)
                } catch (err) {
                    console.error('[VideoService] stream 处理异常:', err)
                }
            }
        }

        // 分发给对应流的订阅者
        const handlers = this.frameHandlers.get(frame.streamId)
        if (handlers) {
            for (const h of handlers) {
                try {
                    h(frame)
                } catch (err) {
                    console.error('[VideoService] frame 处理异常:', err)
                }
            }
        }
    }

    private isKnownStream(streamId: string): boolean {
        return this.knownStreams.has(streamId)
    }

    // 解析二进制成帧协议
    private parseFrame(buf: ArrayBuffer): VideoFrame | null {
        if (buf.byteLength < 4) {
            return null
        }

        const view = new DataView(buf)
        const headerLength = view.getUint32(0, false) // 大端
        if (buf.byteLength < 4 + headerLength) {
            return null
        }

        const headerBytes = new Uint8Array(buf, 4, headerLength)
        const headerText = new TextDecoder().decode(headerBytes)
        let header: { streamId: string; timestamp: number }
        try {
            header = JSON.parse(headerText)
        } catch {
            return null
        }

        if (!header.streamId) {
            return null
        }

        const jpeg = buf.slice(4 + headerLength)

        return {
            streamId: header.streamId,
            timestamp: header.timestamp,
            jpeg
        }
    }
}

export const videoService = new VideoService()
