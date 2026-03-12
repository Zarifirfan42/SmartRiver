/**
 * Datasets, preprocessing, ML prediction API.
 */
import api from './client'

export async function listDatasets() {
  const { data } = await api.get('/datasets/')
  return data
}

export async function uploadDataset(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function runPreprocessing(fileOrDatasetId) {
  if (fileOrDatasetId instanceof File) {
    const form = new FormData()
    form.append('file', fileOrDatasetId)
    const { data } = await api.post('/preprocessing/run', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }
  const { data } = await api.post('/preprocessing/run', null, {
    params: { dataset_id: fileOrDatasetId },
  })
  return data
}

export async function trainModels(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/ml/train', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function predictClassification(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/ml/predict/classification', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function predictForecast(horizon = 7, file = null) {
  const params = { horizon }
  if (file) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/ml/predict/forecast', form, { params, headers: { 'Content-Type': 'multipart/form-data' } })
    return data
  }
  const { data } = await api.post('/ml/predict/forecast', null, { params })
  return data
}

export async function predictAnomaly(file = null) {
  if (file) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/ml/predict/anomaly', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }
  const form = new FormData()
  const { data } = await api.post('/ml/predict/anomaly', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
