document.addEventListener("DOMContentLoaded", () => {
    const data = rawData.map(d => ({
        ...d,
        segment_start: +d.segment_start,
        segment_end: +d.segment_end,
        value: +d.value
    }));

    const margin = { top: 30, right: 20, bottom: 100, left: 200 },
          height = 600 - margin.top - margin.bottom;

    function drawHeatmap() {
        const container = document.getElementById('heatmap-container');
        let containerWidth = container.clientWidth;
        
        const timeExtent = d3.extent([...data.map(d => d.segment_start), ...data.map(d => d.segment_end)]);
        const widthMultiplier = 10;
        const timeScale = d3.scaleLinear()
            .domain(timeExtent)
            .range([0, (containerWidth - margin.left - margin.right) * widthMultiplier]);

        d3.select("#heatmap svg").remove();

        const svgWidth = Math.max(containerWidth, timeScale(timeExtent[1]) + margin.left + margin.right);
        const svg = d3.select("#heatmap").append("svg")
            .attr("width", svgWidth)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const yScale = d3.scaleBand()
            .domain(data.map(d => d.interval_name))
            .range([height, 0])
            .padding(0.1);

        const colorScale = d3.scaleSequential()
            .interpolator(d3.interpolateGreens)
            .domain([0, d3.max(data, d => d.value)]);
        
        // Tooltip div selection
        const tooltip = d3.select("#tooltip");

        svg.selectAll("rect")
            .data(data)
            .enter().append("rect")
            .attr("x", d => timeScale(d.segment_start))
            .attr("width", d => timeScale(d.segment_end) - timeScale(d.segment_start))
            .attr("y", d => yScale(d.interval_name))
            .attr("height", yScale.bandwidth())
            .style("fill", d => colorScale(d.value))
            .on("mouseover", function(event, d) {
                tooltip.transition()
                       .duration(200)
                       .style("opacity", 1);
                tooltip.html(`Interval: ${d.interval_name}<br>Keys: ${d.keys}<br>Value: ${d.values}`)
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
            });

        const xAxis = svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(timeScale).tickFormat(d3.timeFormat("%Y-%m-%d %H:%M:%S")));

        svg.append("g")
            .call(d3.axisLeft(yScale));
    }

    drawHeatmap();
});
