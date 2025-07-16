
document.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById('loader');
    const heatmapContainer = document.getElementById('heatmap-container');
    const zoomControlsContainer = document.getElementById('zoom-controls');
    const intervalSelect = document.getElementById('interval-select');
    const intervalDetails = document.getElementById('interval-details');
    const tableContainer = document.getElementById('table-container');
    const hierarchyContainer = document.getElementById('interval-hierarchy');

    loader.style.display = 'block';

    // When a row in the interval details table is clicked, fetch and display hierarchy
    tableContainer.addEventListener('click', function(event) {
        let target = event.target;
        while (target && target !== tableContainer) {
            if (target.classList.contains('interval-row')) {
                const intervalName = target.getAttribute("data-interval");
                const segmentStart = target.getAttribute("data-segment-start");
                const segmentEnd = target.getAttribute("data-segment-end");
                fetch(`/interval_hierarchy?interval_name=${intervalName}&segment_start=${segmentStart}&segment_end=${segmentEnd}`)
                    .then(response => response.json())
                    .then(data => {
                        const results = data.results;
                        if (!results || results.length === 0) {
                            hierarchyContainer.innerHTML = "<p>No valid rule matches found.</p>";
                            return;
                        }

                        function renderTree(nodeData, depth = 0) {
                            if (!nodeData || !nodeData.data) return '';
                            let html = '';
                            nodeData.data.forEach(node => {
                                const indent = '&nbsp;'.repeat(depth * 4);
                                const rel = node.relationship ? ` (${node.relationship})` : '';
                                html += `<div>${indent}${node.id} [${node.start} - ${node.end}]${rel}</div>`;
                                if (node.children) {
                                    html += renderTree({ data: node.children }, depth + 1);
                                }
                            });
                            return html;
                        }

                        let output = `<h4>Interval Hierarchy for "${data.interval}"</h4>`;
                        results.forEach(tree => {
                            output += renderTree(tree);
                            output += '<hr>';
                        });
                        hierarchyContainer.innerHTML = output;
                    })
                    .catch(err => {
                        console.error('Error fetching interval hierarchy:', err);
                        hierarchyContainer.innerHTML = "<p>Error loading hierarchy.</p>";
                    });
                break;
            }
            target = target.parentElement;
        }
    });

    fetch('/data')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const margin = { top: 150, right: 20, bottom: 30, left: 150 },
                  initialHeight = 600 - margin.top - margin.bottom,
                  width = heatmapContainer.clientWidth - margin.left - margin.right,
                  maxZoomFactor = 20;

            let currentZoomFactor = 1;

            function getRandomColor() {
                const letters = '0123456789ABCDEF';
                let color = '#';
                for (let i = 0; i < 6; i++) {
                    color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }

            function assignColors(intervals) {
                const colors = {};
                intervals.forEach(interval => {
                    colors[interval] = getRandomColor();
                });
                return colors;
            }

            function drawHeatmap(heatmapData, eventData) {
                const intervals = ['events', ...Array.from(new Set(heatmapData.map(d => d.interval_name))).sort()];
                const intervalColors = intervals.reduce((colors, interval) => {
                    colors[interval] = d3.schemeCategory10[intervals.indexOf(interval) % 10];
                    return colors;
                }, {});

                const timeExtent = d3.extent([...heatmapData.map(d => d.segment_start), ...heatmapData.map(d => d.segment_end)]);
                const timeScale = d3.scaleLinear()
                    .domain(timeExtent)
                    .range([0, initialHeight * maxZoomFactor]);

                const xScale = d3.scaleBand()
                    .domain(intervals)
                    .range([0, width])
                    .padding(0.1);

                const tooltip = d3.select("#tooltip");

                d3.select("#heatmap svg").remove();

                const svgHeight = initialHeight * currentZoomFactor + margin.top + margin.bottom;
                const svg = d3.select("#heatmap").append("svg")
                    .attr("width", width + margin.left + margin.right)
                    .attr("height", svgHeight)
                    .append("g")
                    .attr("transform", `translate(${margin.left},${margin.top})`);

                const heatmapGroup = svg.append("g");

                function updateHeatmap() {
                    const zoomedTimeScale = timeScale.copy().range([0, initialHeight * currentZoomFactor]);
                    d3.select("#heatmap svg")
                        .attr("height", initialHeight * currentZoomFactor + margin.top + margin.bottom);

                    heatmapGroup.selectAll("rect")
                        .data(heatmapData)
                        .join("rect")
                        .attr("x", d => xScale(d.interval_name))
                        .attr("width", xScale.bandwidth())
                        .attr("y", d => zoomedTimeScale(d.segment_start))
                        .attr("height", d => zoomedTimeScale(d.segment_end) - zoomedTimeScale(d.segment_start))
                        .style("fill", d => intervalColors[d.interval_name])
                        .on("mouseover", function(event, d) {
                            const eventsInSegment = eventData.filter(ev => ev.timestamp >= d.segment_start && ev.timestamp < d.segment_end);
                            const eventIds = eventsInSegment.map(ev => ev.id).join(", ");
                            tooltip.transition()
                                .duration(200)
                                .style("opacity", 1);
                            tooltip.html(`Interval: ${d.interval_name}<br>Count: ${d.value}<br>Events: ${eventIds}`)
                                .style("left", `${event.pageX + 10}px`)
                                .style("top", `${event.pageY + 10}px`);
                            d3.select(this)
                                .transition()
                                .duration(100)
                                .style("opacity", 0.8);
                        })
                        .on("mouseout", function() {
                            tooltip.transition()
                                .duration(500)
                                .style("opacity", 0);
                            d3.select(this)
                                .transition()
                                .duration(100)
                                .style("opacity", 1);
                        })
                        .on("click", function(event, d) {
                            let intervalTable = `<table>
                                <tr>
                                    <th>Interval Name</th>
                                    <th>Segment Start</th>
                                    <th>Segment End</th>
                                    <th>Keys</th>
                                    <th>Values</th>
                                </tr>
                                <tr class="interval-row" data-interval="${d.interval_name}" data-segment-start="${d.segment_start}" data-segment-end="${d.segment_end}">
                                    <td>${d.interval_name}</td>
                                    <td>${d.segment_start}</td>
                                    <td>${d.segment_end}</td>
                                    <td>${d.keys.join(", ")}</td>
                                    <td>${d.values.join(", ")}</td>
                                </tr>
                            </table>`;

                            let eventsTable = `<table>
                                <tr>
                                    <th>Event ID</th>
                                    <th>Timestamp</th>
                                    <th>Maps</th>
                                    <th>Values</th>
                                </tr>`;
                            const eventsInSegment = eventData.filter(ev => ev.timestamp >= d.segment_start && ev.timestamp < d.segment_end);
                            eventsInSegment.forEach(ev => {
                                eventsTable += `<tr>
                                    <td>${ev.id}</td>
                                    <td>${ev.timestamp}</td>
                                    <td>${ev.event_maps || ''}</td>
                                    <td>${ev.event_values || ''}</td>
                                </tr>`;
                            });
                            eventsTable += `</table>`;

                            tableContainer.innerHTML = intervalTable + eventsTable;
                        });

                    heatmapGroup.selectAll(".event-line")
                        .data(eventData)
                        .join("line")
                        .attr("class", "event-line")
                        .attr("x1", xScale('events'))
                        .attr("x2", xScale('events') + xScale.bandwidth())
                        .attr("y1", d => zoomedTimeScale(d.timestamp))
                        .attr("y2", d => zoomedTimeScale(d.timestamp))
                        .attr("stroke", "grey")
                        .attr("stroke-width", 1);

                    svg.select(".y-axis").remove();
                    svg.append("g")
                        .attr("class", "y-axis")
                        .call(d3.axisLeft(zoomedTimeScale).tickFormat(d => d3.timeFormat("%Y-%m-%d %H:%M:%S")(d * 1000)));

                    svg.select(".x-axis").remove();
                    svg.append("g")
                        .attr("class", "x-axis")
                        .attr("transform", `translate(0,0)`)
                        .call(d3.axisTop(xScale))
                        .selectAll("text")
                        .style("text-anchor", "start")
                        .attr("dx", "0.8em")
                        .attr("dy", "1em")
                        .attr("transform", "rotate(-90)");
                }

                updateHeatmap();

                const zoomLevels = [1, 2, 5, 10, 20];
                const zoomControlSvg = d3.select("#zoom-controls").append("svg")
                    .attr("width", 50)
                    .attr("height", 300)
                    .append("g")
                    .attr("transform", `translate(20,20)`);

                zoomControlSvg.selectAll("circle")
                    .data(zoomLevels)
                    .enter().append("circle")
                    .attr("cx", 15)
                    .attr("cy", (d, i) => i * 50)
                    .attr("r", 15)
                    .style("fill", "#3498db")
                    .on("click", function(event, d) {
                        currentZoomFactor = d;
                        updateHeatmap();
                    });

                zoomControlSvg.selectAll("text")
                    .data(zoomLevels)
                    .enter().append("text")
                    .attr("x", 15)
                    .attr("y", (d, i) => i * 50 + 4)
                    .attr("text-anchor", "middle")
                    .style("fill", "#000")
                    .style("font-weight", "bold")
                    .text(d => `${d}x`)
                    .style("cursor", "pointer")
                    .on("click", function(event, d) {
                        currentZoomFactor = d;
                        updateHeatmap();
                    });
            }

            drawHeatmap(data.heatmap_data, data.event_data);

            // Populate dropdown with specification rules.
            const specData = data.specification_data;
            for (let intervalName in specData) {
                const option = document.createElement('option');
                option.value = intervalName;
                option.textContent = intervalName;
                intervalSelect.appendChild(option);
            }

            intervalSelect.addEventListener('change', function() {
                const selectedInterval = intervalSelect.value;
                const details = specData[selectedInterval];
                intervalDetails.innerHTML = `<h3>${selectedInterval}</h3><ul>${details.map(d => `<li>${d}</li>`).join('')}</ul>`;
            });

            loader.style.display = 'none';
        })
        .catch(error => { 
            console.error('Error fetching data:', error);
            loader.style.display = 'none';
            alert('Failed to load data. Please try again later.');
        });
});
