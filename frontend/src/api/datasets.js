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

export async function deleteDataset(datasetId) {
  const { data } = await api.delete(`/datasets/${datasetId}`)
  return data
}

export async function deleteFilesystemDataset(filePath) {
  const { data } = await api.delete('/datasets/filesystem/remove', {
    params: { file_path: filePath },
  })
  return data
}

/** Train RF + anomaly (+ LSTM if TF) on an uploaded CSV in datasets/uploads. */
export async function trainUploadedModels(filename, lstmEpochs = 12) {
  const { data } = await api.post('/ml/train-uploaded', null, {
    params: { filename, lstm_epochs: lstmEpochs },
  })
  return data
}

/**
 * Run preprocessing. Pass optional numeric datasetId (from upload response) as second arg when sending a File.
 */
export async function runPreprocessing(fileOrDatasetId, datasetId = null) {
  if (fileOrDatasetId instanceof File) {
    const form = new FormData()
    form.append('file', fileOrDatasetId)
    const params = {}
    if (datasetId != null && datasetId !== '') params.dataset_id = datasetId
    const { data } = await api.post('/preprocessing/run', form, {
      params,
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
