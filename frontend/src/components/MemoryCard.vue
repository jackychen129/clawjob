<template>
  <div class="memory-card card">
    <div class="card-header">
      <h3>Agent Memory System</h3>
      <div class="memory-stats">
        <span class="stat">Vectors: {{ memoryStats.vectors }}</span>
        <span class="stat">Collections: {{ memoryStats.collections }}</span>
        <span class="stat">Similarity: {{ memoryStats.similarity }}%</span>
      </div>
    </div>
    <div class="card-content">
      <div class="memory-controls">
        <input 
          v-model="searchQuery" 
          placeholder="Search agent memories..."
          class="search-input"
        />
        <button class="btn btn-primary" @click="searchMemories">
          Search Memories
        </button>
        <button class="btn btn-secondary" @click="clearMemories">
          Clear Memories
        </button>
      </div>
      
      <div class="memory-results" v-if="searchResults.length > 0">
        <div class="memory-item" v-for="memory in searchResults" :key="memory.id">
          <div class="memory-content">
            <p>{{ memory.content }}</p>
            <div class="memory-meta">
              <span class="agent-name">{{ memory.agent_name }}</span>
              <span class="similarity-score">Similarity: {{ memory.similarity_score }}%</span>
              <span class="timestamp">{{ formatDate(memory.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="memory-empty" v-else-if="searchQuery">
        No memories found for "{{ searchQuery }}"
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const searchQuery = ref('')
const searchResults = ref([])
const memoryStats = ref({
  vectors: 0,
  collections: 0,
  similarity: 0
})

onMounted(async () => {
  await loadMemoryStats()
})

async function loadMemoryStats() {
  try {
    const response = await axios.get('/api/agents/memory/stats')
    memoryStats.value = response.data
  } catch (error) {
    console.error('Failed to load memory stats:', error)
  }
}

async function searchMemories() {
  if (!searchQuery.value.trim()) return
  
  try {
    const response = await axios.post('/api/agents/memory/search', {
      query: searchQuery.value,
      limit: 10,
      min_similarity: 0.7
    })
    searchResults.value = response.data.results
  } catch (error) {
    console.error('Failed to search memories:', error)
  }
}

async function clearMemories() {
  if (confirm('Are you sure you want to clear all agent memories?')) {
    try {
      await axios.delete('/api/agents/memory/clear')
      searchResults.value = []
      searchQuery.value = ''
      await loadMemoryStats()
    } catch (error) {
      console.error('Failed to clear memories:', error)
    }
  }
}

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleString()
}
</script>

<style scoped>
.memory-card {
  grid-column: span 2;
}

.memory-stats {
  display: flex;
  gap: 15px;
  margin-top: 8px;
}

.stat {
  background: rgba(138, 43, 226, 0.2);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

.memory-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #4a4a4a;
  border-radius: 4px;
  background: #2d2d2d;
  color: white;
}

.memory-results {
  max-height: 400px;
  overflow-y: auto;
}

.memory-item {
  padding: 12px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border-left: 3px solid #8A2BE2;
}

.memory-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 0.85em;
  color: #aaa;
}

.memory-empty {
  text-align: center;
  color: #888;
  padding: 20px;
}
</style>
</template>