/** Dispatched after admin upload/delete changes dashboard readings (cross-tab refresh). */
export const SMARTRIVER_DATASET_CHANGED = 'smartriver-dataset-changed'

export function notifyDatasetChanged(detail = {}) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(SMARTRIVER_DATASET_CHANGED, { detail }))
}
