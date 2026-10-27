export const COLORS = {
  claude: '#34d399',
  trae: '#5b9dff',
  cost: '#f5b545',
  grid: '#16202c',
  axis: '#23303f',
  text: '#8698ac'
}

export function categoryAxis(labels, extra = {}) {
  return {
    type: 'category',
    data: labels,
    axisTick: { show: false },
    axisLine: { lineStyle: { color: COLORS.axis } },
    axisLabel: { color: COLORS.text, fontSize: 10 },
    ...extra
  }
}

export function valueAxis(extra = {}) {
  return {
    type: 'value',
    splitLine: { lineStyle: { color: COLORS.grid } },
    axisLabel: { color: COLORS.text, fontSize: 10 },
    ...extra
  }
}

export const tooltip = {
  trigger: 'axis',
  backgroundColor: '#0f1620',
  borderColor: '#2a3a4d',
  borderWidth: 1,
  padding: [8, 11],
  textStyle: { color: '#e8eef6', fontSize: 11 },
  axisPointer: { lineStyle: { color: '#31445a' } }
}

export const legend = {
  icon: 'circle',
  itemWidth: 7,
  itemHeight: 7,
  top: 0,
  right: 0,
  textStyle: { color: COLORS.text, fontSize: 11 }
}
