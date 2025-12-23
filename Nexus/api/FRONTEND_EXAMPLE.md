# Frontend Integration Example

This document shows how to connect a separate frontend application to your Spring Boot API.

## Quick Start: Frontend API Client

### React Example

```javascript
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

class ApiService {
  // Helper method for making requests
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        // Add auth token when authentication is implemented:
        // 'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      ...options
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  }

  // GET /api/options
  async getOptions() {
    return this.request('/api/options');
  }

  // GET /api/options/{id}
  async getOptionById(id) {
    return this.request(`/api/options/${id}`);
  }

  // GET /api/options/symbol/{symbol}
  async getOptionsBySymbol(symbol) {
    return this.request(`/api/options/symbol/${symbol}`);
  }

  // POST /api/options
  async createOption(option) {
    return this.request('/api/options', {
      method: 'POST',
      body: JSON.stringify(option)
    });
  }

  // PUT /api/options/{id}
  async updateOption(id, option) {
    return this.request(`/api/options/${id}`, {
      method: 'PUT',
      body: JSON.stringify(option)
    });
  }

  // DELETE /api/options/{id}
  async deleteOption(id) {
    return this.request(`/api/options/${id}`, {
      method: 'DELETE'
    });
  }
}

export default new ApiService();
```

### Using the API Service in a React Component

```javascript
// frontend/src/components/OptionsList.jsx
import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

function OptionsList() {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadOptions();
  }, []);

  const loadOptions = async () => {
    try {
      setLoading(true);
      const data = await apiService.getOptions();
      setOptions(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (newOption) => {
    try {
      const created = await apiService.createOption(newOption);
      setOptions([...options, created]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await apiService.deleteOption(id);
      setOptions(options.filter(opt => opt.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Options</h1>
      {options.map(option => (
        <div key={option.id}>
          <h3>{option.symbol} - {option.optionType}</h3>
          <p>Strike: ${option.strikePrice}</p>
          <button onClick={() => handleDelete(option.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

export default OptionsList;
```

## Vue.js Example

```javascript
// frontend/src/services/api.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8081';

export const apiService = {
  async request(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  },

  async getOptions() {
    return this.request('/api/options');
  },

  async createOption(option) {
    return this.request('/api/options', {
      method: 'POST',
      body: JSON.stringify(option)
    });
  }
};
```

```vue
<!-- frontend/src/components/OptionsList.vue -->
<template>
  <div>
    <h1>Options</h1>
    <div v-if="loading">Loading...</div>
    <div v-else>
      <div v-for="option in options" :key="option.id">
        <h3>{{ option.symbol }} - {{ option.optionType }}</h3>
        <p>Strike: ${{ option.strikePrice }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import { apiService } from '../services/api';

export default {
  data() {
    return {
      options: [],
      loading: true
    };
  },
  async mounted() {
    try {
      this.options = await apiService.getOptions();
    } catch (error) {
      console.error('Failed to load options:', error);
    } finally {
      this.loading = false;
    }
  }
};
</script>
```

## Angular Example

```typescript
// frontend/src/app/services/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const API_BASE_URL = 'http://localhost:8081';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) {}

  getOptions(): Observable<Option[]> {
    return this.http.get<Option[]>(`${API_BASE_URL}/api/options`);
  }

  getOptionById(id: number): Observable<Option> {
    return this.http.get<Option>(`${API_BASE_URL}/api/options/${id}`);
  }

  createOption(option: Option): Observable<Option> {
    return this.http.post<Option>(`${API_BASE_URL}/api/options`, option);
  }

  updateOption(id: number, option: Option): Observable<Option> {
    return this.http.put<Option>(`${API_BASE_URL}/api/options/${id}`, option);
  }

  deleteOption(id: number): Observable<void> {
    return this.http.delete<void>(`${API_BASE_URL}/api/options/${id}`);
  }
}
```

```typescript
// frontend/src/app/components/options-list.component.ts
import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { Option } from '../models/option';

@Component({
  selector: 'app-options-list',
  template: `
    <h1>Options</h1>
    <div *ngIf="loading">Loading...</div>
    <div *ngFor="let option of options">
      <h3>{{ option.symbol }} - {{ option.optionType }}</h3>
      <p>Strike: ${{ option.strikePrice }}</p>
    </div>
  `
})
export class OptionsListComponent implements OnInit {
  options: Option[] = [];
  loading = true;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.apiService.getOptions().subscribe({
      next: (data) => {
        this.options = data;
        this.loading = false;
      },
      error: (error) => {
        console.error('Failed to load options:', error);
        this.loading = false;
      }
    });
  }
}
```

## Environment Configuration

### React (.env)
```
REACT_APP_API_URL=http://localhost:8081
```

### Vue/Vite (.env)
```
VITE_API_URL=http://localhost:8081
```

### Angular (environment.ts)
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8081'
};
```

## Testing the Connection

### 1. Start the API
```bash
cd Nexus/api
./mvnw spring-boot:run
```

### 2. Test API directly
```bash
curl http://localhost:8081/api/options
```

### 3. Start Frontend
```bash
cd frontend
npm start  # or npm run dev
```

### 4. Check Browser Console
- Open browser DevTools (F12)
- Check Network tab for API calls
- Verify CORS headers are present

## Common Issues

### CORS Error
**Problem**: `Access-Control-Allow-Origin` error in browser

**Solution**: 
- Check `CorsConfig.java` includes your frontend URL
- Ensure API is running
- Check browser console for exact error

### Connection Refused
**Problem**: Cannot connect to API

**Solution**:
- Verify API is running on port 8081
- Check firewall settings
- Verify API_URL in frontend matches API port

### 404 Not Found
**Problem**: Endpoint not found

**Solution**:
- Verify endpoint path matches exactly: `/api/options`
- Check API logs for registered endpoints
- Ensure `@RequestMapping("/api/options")` in controller

## Next Steps

1. **Add Authentication**: Update API client to include JWT tokens
2. **Error Handling**: Add global error handler in frontend
3. **Loading States**: Show loading indicators during API calls
4. **Caching**: Implement response caching for better performance
5. **Real-time Updates**: Consider WebSockets for live data


