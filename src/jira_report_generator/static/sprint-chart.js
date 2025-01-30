const VERSION_TAB_ID = 1;

const GET_SPRINT_PROPERTY_PATH = (sprintTabId, sprintProperty) => `/api/jira/board/${sprintTabId}/get-sprints-property/${sprintProperty}`;
const SET_SPRINT_PROPERTY_PATH = '/api/jira/set-sprint-property';
const LIMIT_SPRINT_PROPERTY = 'limit';

const CHARTS = new Map();

function createSprintChart(sprintTabContent, canvas) {
    const sprints = getSprintChartData(sprintTabContent);
    
    const labels = sprints.map(sprint => sprint.releaseDate);

    return new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Limit',
                    data: sprints.map(sprint => sprint.limitHours),
                },
                {
                    label: 'Spent',
                    data: sprints.map(sprint => sprint.spentHours),
                }
            ],
        },
    });
}
  
function getSprintChartData(sprintTabContent) {
    const rows = sprintTabContent.querySelectorAll(`[data-row-sprint-id]`);
  
    const sprints = [];
    for (const row of rows) {
      const limitHours = parseFloat(row.querySelector('[data-row-sprint-column-name="limit"]').textContent);
      const spentHours = parseFloat(row.querySelector('[data-row-sprint-column-name="spent"]').textContent);
      const releaseDate = row.querySelectorAll('[class="date"]')[1].textContent;
  
      sprints.push({
        limitHours,
        spentHours,
        releaseDate
      })
    }
  
    return sprints;
}

function initCanvas() {
    const sprintTab = this;
    const sprintTabId = sprintTab.getAttribute('data-tab-header-id');
    const sprintTabContent = document.querySelector(`[data-tab-content-id="${sprintTabId}"]`);

    let canvas = sprintTabContent.querySelector('canvas');

    if (canvas === null) {
        canvas = document.createElement('canvas');
        const canvasContainer = document.createElement('div');
        canvasContainer.style = 'height: 50vh';
        canvasContainer.appendChild(canvas);
        sprintTabContent.prepend(canvasContainer);
    }

    if (CHARTS.has(sprintTabId)) {
        return;
    }

    const newChart = createSprintChart(sprintTabContent, canvas);
    CHARTS.set(sprintTabId, newChart);
}

async function initLimitColumn(sprintTab) {
    const sprintTabId = sprintTab.getAttribute('data-tab-header-id');
    const sprintTabContent = document.querySelector(`[data-tab-content-id="${sprintTabId}"]`);
    const rows = sprintTabContent.querySelectorAll(`[data-row-sprint-id]`);

    const response = await fetch(GET_SPRINT_PROPERTY_PATH(sprintTabId, LIMIT_SPRINT_PROPERTY));
    const limitProperties = await response.json();

    for (const row of rows) {
        const sprintId = parseInt(row.getAttribute('data-row-sprint-id'));
        const limitProperty = limitProperties
            .find(sprintProperty => sprintProperty.sprint_id === sprintId);
        
        const limitCell = row.querySelector('[data-row-sprint-column-name="limit"]');
        limitCell.textContent = limitProperty.value;
        limitCell.style = 'cursor:pointer';
        limitCell.addEventListener('click', async () => await updateLimit(limitCell, row, sprintTabId, sprintId));
    }
}

async function updateLimit(limitCell, row, sprintTabId, sprintId) {
    const newLimitString = prompt("Enter limit");
    const newLimit = parseFloat(newLimitString);

    if (isNaN(newLimit)) {
        return;
    }

    await fetch(SET_SPRINT_PROPERTY_PATH, { 
        method: 'put', 
        body: JSON.stringify({ 
            sprint_id: sprintId, 
            name: LIMIT_SPRINT_PROPERTY, 
            value: newLimit
        })
    });

    limitCell.textContent = newLimit;

    const chart = CHARTS.get(sprintTabId);
    if (chart === undefined) {
        return;
    }

    const releaseDate = row.querySelectorAll('[class="date"]')[1].textContent;
    updateChart(chart, newLimit, releaseDate);
}

function updateChart(chart, newLimit, releaseDate) {
    const releaseDateIndex = chart.data.labels.indexOf(releaseDate);
    const limitDataset = chart.data.datasets.find(dataset => dataset.label === 'Limit');
    limitDataset.data[releaseDateIndex] = newLimit;
    chart.update();
}

const sprintTabs = document.querySelectorAll(`.tab-header:not([data-tab-header-id="${VERSION_TAB_ID}"])`);

for(const sprintTab of sprintTabs) {
    await initLimitColumn(sprintTab);
    sprintTab.addEventListener('click', initCanvas);
}

const activeTab = document.querySelector('.tab-header.active');
const activeTabId = activeTab.getAttribute('data-tab-header-id');

if (activeTabId !== VERSION_TAB_ID) {
    initCanvas.apply(activeTab);
}