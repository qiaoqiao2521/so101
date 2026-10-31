<script setup>
defineProps({
  eventFeed: { type: Array, required: true },
  feedTone: { type: Function, required: true },
});
</script>

<template>
  <section class="timeline-panel">
    <div class="section-head compact">
      <p class="eyebrow">系统事件</p>
      <h2>系统时间线</h2>
    </div>
    <div class="timeline-list">
      <article v-for="event in eventFeed" :key="event.id" class="timeline-item" :class="feedTone(event.type)">
        <header>
          <strong>{{ event.title }}</strong>
          <span>{{ event.time }}</span>
        </header>
        <p>{{ event.detail }}</p>
      </article>
    </div>
  </section>
</template>
