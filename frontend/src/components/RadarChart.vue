<script setup lang="ts">
import { computed } from 'vue'

interface Dimension {
  name: string
  value: number | null
}

const props = withDefaults(
  defineProps<{
    dimensions: Dimension[]
    max?: number
    size?: number
  }>(),
  { max: 100, size: 210 },
)

const cx = computed(() => props.size / 2)
const cy = computed(() => props.size / 2)
const R = computed(() => props.size / 2 - 30)

const n = computed(() => Math.max(props.dimensions.length, 1))
const angleFor = (i: number) => ((-90 + (360 / n.value) * i) * Math.PI) / 180

function pointAt(i: number, ratio: number): [number, number] {
  const a = angleFor(i)
  return [cx.value + R.value * ratio * Math.cos(a), cy.value + R.value * ratio * Math.sin(a)]
}

const levels = [0.25, 0.5, 0.75, 1]
const gridPolys = computed(() =>
  levels.map((lv) => props.dimensions.map((_, i) => pointAt(i, lv).join(',')).join(' ')),
)
const axisLines = computed(() =>
  props.dimensions.map((_, i) => {
    const [x, y] = pointAt(i, 1)
    return { x1: cx.value, y1: cy.value, x2: x, y2: y }
  }),
)
const dataPoints = computed(() =>
  props.dimensions.map((d, i) => pointAt(i, ((d.value ?? 0) / props.max))),
)
const dataPoly = computed(() => dataPoints.value.map((p) => p.join(',')).join(' '))
const labels = computed(() =>
  props.dimensions.map((d, i) => {
    const [x, y] = pointAt(i, 1)
    return { x, y, name: d.name, value: d.value }
  }),
)
</script>

<template>
  <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="radar">
    <polygon v-for="(poly, li) in gridPolys" :key="'g' + li" :points="poly" class="radar-grid" />
    <line
      v-for="(ln, li) in axisLines"
      :key="'a' + li"
      :x1="ln.x1"
      :y1="ln.y1"
      :x2="ln.x2"
      :y2="ln.y2"
      class="radar-axis"
    />
    <polygon :points="dataPoly" class="radar-area" />
    <circle v-for="(p, i) in dataPoints" :key="'p' + i" :cx="p[0]" :cy="p[1]" r="3" class="radar-dot" />
    <text
      v-for="(lb, i) in labels"
      :key="'l' + i"
      :x="lb.x"
      :y="lb.y - 4"
      class="radar-label"
      text-anchor="middle"
      dominant-baseline="middle"
    >
      {{ lb.name }}
    </text>
    <text
      v-for="(lb, i) in labels"
      :key="'v' + i"
      :x="lb.x"
      :y="lb.y + 11"
      class="radar-value"
      text-anchor="middle"
      dominant-baseline="middle"
    >
      {{ lb.value != null ? lb.value : '-' }}
    </text>
  </svg>
</template>

<style scoped>
.radar-grid {
  fill: none;
  stroke: rgba(99, 102, 241, 0.2);
  stroke-width: 1;
}
.radar-axis {
  stroke: rgba(99, 102, 241, 0.28);
  stroke-width: 1;
}
.radar-area {
  fill: rgba(99, 102, 241, 0.22);
  stroke: #6366f1;
  stroke-width: 2;
}
.radar-dot {
  fill: #6366f1;
}
.radar-label {
  fill: #475569;
  font-size: 12px;
  font-weight: 600;
}
.radar-value {
  fill: #1e293b;
  font-size: 11px;
  font-weight: 700;
}
</style>
