<template>
  <div class="task-card">
    <div class="card-header">
      <h3>{{ task.title }}</h3>
      <span class="task-status" :class="task.status.toLowerCase()">{{ task.status }}</span>
    </div>
    <div class="card-content">
      <p class="task-description">{{ task.description }}</p>
      <div class="task-details">
        <div class="task-info">
          <span class="task-agent">Assigned Agent: {{ task.agent_name }}</span>
          <span class="task-priority">Priority: {{ task.priority }}</span>
        </div>
        <div class="task-timeline">
          <span class="task-created">Created: {{ formatDate(task.created_at) }}</span>
          <span class="task-updated">Updated: {{ formatDate(task.updated_at) }}</span>
        </div>
      </div>
      <div class="task-actions">
        <button type="button" class="btn btn-primary" @click="startTask">Start Task</button>
        <button type="button" class="btn btn-secondary" @click="pauseTask">Pause Task</button>
        <button type="button" class="btn btn-danger" @click="cancelTask">Cancel Task</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

const startTask = () => {
  // Start task logic
  console.log('Starting task:', props.task.id)
}

const pauseTask = () => {
  // Pause task logic
  console.log('Pausing task:', props.task.id)
}

const cancelTask = () => {
  // Cancel task logic
  console.log('Canceling task:', props.task.id)
}
</script>

<style scoped>
.task-card {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 16px;
  padding: 20px;
  margin: 15px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 14px 30px rgba(0,0,0,0.18);
  transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 300ms cubic-bezier(0.4, 0, 0.2, 1), border-color 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  color: #ffffff;
  font-size: 1.2em;
  margin: 0;
}

.task-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8em;
  font-weight: bold;
}

.task-status.pending {
  background: #ff9800;
  color: #000000;
}

.task-status.running {
  background: #4caf50;
  color: #ffffff;
}

.task-status.completed {
  background: #2196f3;
  color: #ffffff;
}

.task-status.failed {
  background: #f44336;
  color: #ffffff;
}

.task-description {
  color: #b0b0b0;
  margin-bottom: 15px;
  line-height: 1.4;
}

.task-details {
  margin-bottom: 15px;
}

.task-info, .task-timeline {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.task-agent, .task-priority, .task-created, .task-updated {
  color: #8a2be2;
  font-size: 0.9em;
}

.task-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.2s ease;
}

.btn-primary {
  background: #8a2be2;
  color: white;
}

.btn-primary:hover {
  background: #7a1bd2;
}

.btn-secondary {
  background: transparent;
  color: #8a2be2;
  border: 1px solid #8a2be2;
}

.btn-secondary:hover {
  background: #8a2be2;
  color: white;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #d32f2f;
}
</style>
</template>