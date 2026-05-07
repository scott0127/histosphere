<template>
  <div class="w-full h-full relative bg-[#d4c5b0] overflow-hidden">
    <!-- Map Container -->
    <div id="map" class="w-full h-full z-0"></div>

    <!-- Event Info Overlay (when a pin is clicked) -->
    <div 
      v-if="selectedEvent" 
      class="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-11/12 max-w-md bg-history-cream border-2 border-history-dark rounded-xl shadow-2xl p-6 z-[1000] animate-slide-up font-serif"
    >
      <button 
        @click="selectedEvent = null" 
        class="absolute top-2 right-2 text-history-brown hover:text-history-dark"
      >
        <Icon name="mdi:close" class="w-6 h-6" />
      </button>
      
      <h3 class="text-xl font-bold text-history-dark mb-1">{{ selectedEvent.name }}</h3>
      <p class="text-sm text-history-brown mb-3 italic">{{ selectedEvent.geographic_location }} • {{ selectedEvent.century }} 世紀</p>
      
      <p class="text-sm text-history-dark/80 mb-4 line-clamp-3">
        {{ selectedEvent.description || selectedEvent.context }}
      </p>
      
      <button 
        @click="$emit('enter-story', selectedEvent)"
        class="w-full py-2 bg-history-dark hover:bg-history-brown text-history-paper font-bold rounded shadow transition-colors flex items-center justify-center gap-2"
      >
        <Icon name="mdi:login" class="w-4 h-4" />
        進入歷史現場
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, onUnmounted } from 'vue';
import type { HistoricalEvent, Persona } from '~/types';
import 'leaflet/dist/leaflet.css';

// Dynamic import for Leaflet to avoid SSR issues
let L: any;

interface EventWithPersonas extends HistoricalEvent {
  personas: Persona[];
}

const props = defineProps<{
  events: EventWithPersonas[];
}>();

const emit = defineEmits<{
  (e: 'enter-story', event: EventWithPersonas): void;
}>();

const selectedEvent = ref<EventWithPersonas | null>(null);
let map: any = null;
let markers: any[] = [];

onMounted(async () => {
  if (process.client) {
    L = (await import('leaflet')).default;
    
    // Initialize Map
    // Set world bounds to prevent infinite panning
    const worldBounds = L.latLngBounds(
      L.latLng(-85, -180), // Southwest corner
      L.latLng(85, 180)    // Northeast corner
    );
    
    map = L.map('map', {
      center: [20, 0],
      zoom: 2,
      minZoom: 2,
      maxZoom: 6,
      zoomControl: false,
      attributionControl: false,
      maxBounds: worldBounds,
      maxBoundsViscosity: 1.0 // Makes bounds hard limit (1.0) vs soft limit (0.0)
    });

    // Add a tile layer with blue ocean and clear borders
    // Using Esri WorldStreetMap for natural ocean colors
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri',
      maxZoom: 20
    }).addTo(map);

    // Remove filter to show original colors
    // const mapContainer = document.getElementById('map');
    // if (mapContainer) {
    //   mapContainer.style.filter = 'sepia(0.3) contrast(1.15) brightness(0.95) saturate(0.8)';
    // }

    updateMarkers();
  }
});

// Fix for Leaflet default icon not showing
const getIcon = () => {
  if (!L) return null;
  
  // Custom SVG Icon for "Historical Pin"
  const svgIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#3E2723" stroke="#F5F5DC" stroke-width="1.5">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  `;
  
  return L.divIcon({
    className: 'custom-pin',
    html: svgIcon,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32]
  });
};

const updateMarkers = () => {
  if (!map || !L) return;

  // Clear existing markers
  markers.forEach(marker => map.removeLayer(marker));
  markers = [];

  props.events.forEach(event => {
    if (event.latitude && event.longitude) {
      const marker = L.marker([event.latitude, event.longitude], { icon: getIcon() })
        .addTo(map)
        .on('click', () => {
          selectedEvent.value = event;
          map.flyTo([event.latitude, event.longitude], 4, { duration: 1.5 });
        });
      markers.push(marker);
    }
  });
};

watch(() => props.events, () => {
  updateMarkers();
}, { deep: true });

onUnmounted(() => {
  if (map) {
    map.remove();
  }
});
</script>

<style>
/* Global styles for Leaflet popup/icon if needed */
.custom-pin svg {
  filter: drop-shadow(2px 4px 6px rgba(0,0,0,0.3));
  transition: transform 0.2s;
}
.custom-pin:hover svg {
  transform: scale(1.2) translateY(-5px);
}
@keyframes slide-up {
  from { opacity: 0; transform: translate(-50%, 20px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
.animate-slide-up {
  animation: slide-up 0.3s ease-out;
}


</style>
