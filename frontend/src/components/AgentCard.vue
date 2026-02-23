<template>
  <div class="agent-card">
    <div class="card-header">
      <h3>{{ agent.name }}</h3>
      <span class="agent-status" :class="agent.status">{{ agent.status }}</span>
    </div>
    <div class="card-content">
      <p class="agent-description">{{ agent.description }}</p>
      <div class="agent-stats">
        <div class="stat-item">
          <span class="stat-label">Tasks Completed</span>
          <span class="stat-value">{{ agent.tasksCompleted }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Memory Items</span>
          <span class="stat-value">{{ agent.memoryItems }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Tools Available</span>
          <span class="stat-value">{{ agent.tools.length }}</span>
        </div>
      </div>
      <div class="agent-actions">
        <button class="btn btn-secondary" @click="startTask(agent.id)">Start Task</button>
        <button class="btn btn-outline" @click="viewMemory(agent.id)">View Memory</button>
        <button class="btn btn-outline" @click="manageTools(agent.id)">Manage Tools</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  agent: {
    type: Object,
    required: true
  }
})

const startTask = (agentId) => {
  // Start a new task for this agent
  console.log('Starting task for agent:', agentId)
}

const viewMemory = (agentId) => {
  // View agent's memory
  console.log('Viewing memory for agent:', agentId)
}

const manageTools = (agentId) => {
  // Manage agent's tools
  console.log('Managing tools for agent:', agentId)
}
</script>

<style scoped>
.agent-card {
  background: #2d2d2d;
  border-radius: 8px;
  padding: 20px;
  margin: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.agent-card:hover {
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
  margin: 0;
  font-size: 1.2em;
}

.agent-status {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: bold;
}

.agent-status.active {
  background: #4CAF50;
  color: white;
}

.agent-status.idle {
  background: #FF9800;
  color: white;
}

.agent-status.offline {
  background: #f44336;
  color: white;
}

.agent-description {
  color: #b0b0b0;
  margin-bottom: 20px;
  line-height: 1.5;
}

.agent-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  color: #888888;
  font-size: 0.9em;
  display: block;
  margin-bottom: 5px;
}

.stat-value {
  color: #ffffff;
  font-size: 1.2em;
  font-weight: bold;
  display: block;
}

.agent-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
}

.btn-secondary {
  background: #8A2BE2;
  color: white;
}

.btn-secondary:hover {
  background: #7a1ad2;
}

.btn-outline {
  background: transparent;
  color: #8A2BE2;
  border: 1px solid #8A2BE2;
}

.btn-outline:hover {
  background: rgba(138, 43, 226, 0.1);
}
</style>