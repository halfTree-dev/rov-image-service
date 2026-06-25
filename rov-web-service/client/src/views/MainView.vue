<template>
    <div class="main-view">
        <div class="sidebar">
            <SideBar />
        </div>
        <div class="video-area">
            <VideoContainer />
        </div>
    </div>
</template>

<script setup lang="ts">
import SideBar from '../components/SideBar.vue';
import VideoContainer from '../components/VideoContainer.vue';
</script>

<style>
html,
body,
#app {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
}

.main-view {
    display: flex;
    width: 100vw;
    height: 100vh;
}

.sidebar {
    flex: 0 0 240px;
    height: 100%;
    border-right: 1px solid #333;
}

.video-area {
    flex: 1 1 auto;
    height: 100%;
    min-width: 0;
}
</style>
