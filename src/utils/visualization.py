import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os
import json

class PerformanceVisualizer:
    """Generates interactive visualizations for performance test results."""
    
    def __init__(self, output_dir='reports'):
        """Initialize visualizer with output directory."""
        self.output_dir = output_dir
        self.data_dir = os.path.join(output_dir, 'data')
        self.export_dir = os.path.join(output_dir, 'exports')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Set default Plotly template
        pio.templates.default = "plotly_white"
    
    def save_test_data(self, test_data, run_id=None):
        """Save test data for future comparisons."""
        if run_id is None:
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        data_file = os.path.join(self.data_dir, f'test_data_{run_id}.json')
        with open(data_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        
        return run_id
    
    def load_test_data(self, run_id):
        """Load test data from a previous run."""
        data_file = os.path.join(self.data_dir, f'test_data_{run_id}.json')
        with open(data_file, 'r') as f:
            return json.load(f)
    
    def list_available_runs(self):
        """List available test runs for comparison."""
        runs = []
        for file in os.listdir(self.data_dir):
            if file.startswith('test_data_') and file.endswith('.json'):
                run_id = file[10:-5]  # Remove 'test_data_' and '.json'
                runs.append(run_id)
        return sorted(runs, reverse=True)
    
    def plot_transform_durations(self, shape_counts, durations, test_type='batch', 
                               comparison_data=None, filters=None):
        """Generate interactive line plot of transform durations vs shape count."""
        # Apply filters if provided
        if filters:
            filtered_indices = self._apply_filters(shape_counts, filters)
            shape_counts = [shape_counts[i] for i in filtered_indices]
            durations = [durations[i] for i in filtered_indices]
        
        # Create figure based on comparison mode
        if comparison_data:
            fig = make_subplots(rows=1, cols=2, 
                              subplot_titles=("Current Run", "Comparison Run"),
                              horizontal_spacing=0.1)
            
            # Current run
            self._add_duration_traces(fig, shape_counts, durations, row=1, col=1)
            
            # Comparison run
            comp_shape_counts = comparison_data['shape_counts']
            comp_durations = comparison_data['durations']
            if filters:
                filtered_indices = self._apply_filters(comp_shape_counts, filters)
                comp_shape_counts = [comp_shape_counts[i] for i in filtered_indices]
                comp_durations = [comp_durations[i] for i in filtered_indices]
            self._add_duration_traces(fig, comp_shape_counts, comp_durations, row=1, col=2)
            
            fig.update_layout(height=600)
        else:
            fig = go.Figure()
            self._add_duration_traces(fig, shape_counts, durations)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{test_type.title()} Transform Duration vs Shape Count',
                x=0.5,
                font=dict(size=20)
            ),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        # Add range slider for time series exploration
        fig.update_xaxes(rangeslider_visible=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/transform_duration_{test_type}_{timestamp}.html'
        
        # Prepare data for JavaScript
        if comparison_data:
            js_data = f"""
            <script>
            window.currentData = {{
                shape_counts: {json.dumps(shape_counts)},
                durations: {json.dumps(durations)}
            }};
            window.comparisonData = {{
                current: {{
                    shape_counts: {json.dumps(shape_counts)},
                    durations: {json.dumps(durations)}
                }},
                comparison: {{
                    shape_counts: {json.dumps(comp_shape_counts)},
                    durations: {json.dumps(comp_durations)}
                }}
            }};
            </script>
            """
        else:
            js_data = f"""
            <script>
            window.currentData = {{
                shape_counts: {json.dumps(shape_counts)},
                durations: {json.dumps(durations)}
            }};
            window.comparisonData = null;
            </script>
            """
        
        # Add interactive controls and export functionality
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={
                'displayModeBar': True,
                'responsive': True,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']
            },
            post_script=js_data
        )
        
        return filename
    
    def _add_duration_traces(self, fig, shape_counts, durations, row=1, col=1):
        """Add duration and trend traces to the figure."""
        # Duration scatter plot
        fig.add_trace(
            go.Scatter(
                x=shape_counts,
                y=durations,
                mode='lines+markers',
                name='Duration (ms)',
                line=dict(width=2, color='#1f77b4'),
                marker=dict(size=10),
                hovertemplate='Shape Count: %{x}<br>Duration: %{y:.2f} ms<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Trend line
        z = np.polyfit(shape_counts, durations, 1)
        p = np.poly1d(z)
        trend_x = np.array(shape_counts)
        trend_y = p(trend_x)
        fig.add_trace(
            go.Scatter(
                x=trend_x,
                y=trend_y,
                mode='lines',
                name=f'Trend (slope: {z[0]:.2f})',
                line=dict(dash='dash', color='#ff7f0e'),
                hovertemplate='Shape Count: %{x}<br>Predicted: %{y:.2f} ms<extra></extra>'
            ),
            row=row, col=col
        )
    
    def _apply_filters(self, values, filters):
        """Apply filters to data series."""
        indices = []
        for i, value in enumerate(values):
            include = True
            for filter_key, filter_value in filters.items():
                if filter_key == 'min_value' and value < filter_value:
                    include = False
                elif filter_key == 'max_value' and value > filter_value:
                    include = False
                elif filter_key == 'value_range':
                    min_val, max_val = filter_value
                    if value < min_val or value > max_val:
                        include = False
            if include:
                indices.append(i)
        return indices
    
    def plot_memory_usage(self, shape_counts, memory_usage, test_type='batch'):
        """Generate interactive bar plot of memory usage per test scenario."""
        fig = go.Figure()
        
        # Add memory usage bars
        fig.add_trace(go.Bar(
            x=shape_counts,
            y=memory_usage,
            name='Memory Usage',
            marker_color='#2ecc71',
            opacity=0.7,
            hovertemplate='Shape Count: %{x}<br>Memory: %{y:.1f} MB<extra></extra>'
        ))
        
        # Add value labels on top of bars
        for i, value in enumerate(memory_usage):
            fig.add_annotation(
                x=shape_counts[i],
                y=value,
                text=f'{value:.1f} MB',
                showarrow=False,
                yshift=10,
                font=dict(size=12)
            )
        
        fig.update_layout(
            title=dict(
                text=f'Memory Usage per {test_type.title()} Test Scenario',
                x=0.5,
                font=dict(size=20)
            ),
            xaxis_title=dict(text='Shape Count', font=dict(size=14)),
            yaxis_title=dict(text='Memory Usage (MB)', font=dict(size=14)),
            hovermode='closest',
            showlegend=False,
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.output_dir}/memory_usage_{test_type}_{timestamp}.html'
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={'displayModeBar': True, 'responsive': True}
        )
        
        return filename
    
    def plot_performance_scatter(self, x_values, y_values, x_label, y_label, title):
        """Generate interactive scatter plot with trend line."""
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='markers',
            name='Data Points',
            marker=dict(
                size=12,
                color='#3498db',
                opacity=0.6,
                line=dict(width=1, color='#2980b9')
            ),
            hovertemplate=f'{x_label}: %{{x}}<br>{y_label}: %{{y:.2f}}<extra></extra>'
        ))
        
        # Add trend line
        z = np.polyfit(x_values, y_values, 1)
        p = np.poly1d(z)
        trend_x = np.array(x_values)
        trend_y = p(trend_x)
        fig.add_trace(go.Scatter(
            x=trend_x,
            y=trend_y,
            mode='lines',
            name=f'Trend (slope: {z[0]:.2f})',
            line=dict(dash='dash', color='#e74c3c'),
            hovertemplate=f'{x_label}: %{{x}}<br>Predicted {y_label}: %{{y:.2f}}<extra></extra>'
        ))
        
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                font=dict(size=20)
            ),
            xaxis_title=dict(text=x_label, font=dict(size=14)),
            yaxis_title=dict(text=y_label, font=dict(size=14)),
            hovermode='closest',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            margin=dict(t=100, l=80, r=80, b=80)
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = title.lower().replace(' ', '_')
        filename = f'{self.output_dir}/scatter_{safe_title}_{timestamp}.html'
        fig.write_html(
            filename,
            include_plotlyjs='cdn',
            full_html=True,
            config={'displayModeBar': True, 'responsive': True}
        )
        
        return filename
    
    def generate_html_report(self, report_data, chart_files):
        """Generate HTML report with embedded interactive visualizations."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = f'{self.output_dir}/performance_report_{timestamp}.html'
        
        # Add JavaScript for interactive filtering and export functionality
        js_code = """
        <script>
        // Data validation utilities
        function isValidNumber(value) {
            return typeof value === 'number' && !isNaN(value) && isFinite(value);
        }
        
        function sanitizeNumber(value, decimals = 2) {
            if (!isValidNumber(value)) {
                return 'N/A';
            }
            return Number(value).toFixed(decimals);
        }
        
        function validateDataArrays(arrays, names) {
            if (!arrays || !Array.isArray(arrays) || arrays.length === 0) {
                throw new Error('No data arrays provided');
            }
            
            const length = arrays[0].length;
            for (let i = 1; i < arrays.length; i++) {
                if (!Array.isArray(arrays[i]) || arrays[i].length !== length) {
                    throw new Error(`${names[i]} array length mismatch: expected ${length}, got ${arrays[i].length}`);
                }
            }
            return length;
        }
        
        function sanitizeDataForExport(data) {
            if (!data || !data.shape_counts || !data.durations) {
                throw new Error('Invalid data structure');
            }
            
            try {
                validateDataArrays(
                    [data.shape_counts, data.durations],
                    ['shape_counts', 'durations']
                );
                
                return {
                    shape_counts: data.shape_counts.map(count => 
                        isValidNumber(count) ? Math.round(count) : 'N/A'
                    ),
                    durations: data.durations.map(duration => 
                        sanitizeNumber(duration, 2)
                    )
                };
            } catch (error) {
                throw new Error(`Data validation failed: ${error.message}`);
            }
        }
        
        function sanitizeComparisonDataForExport(data) {
            if (!data || !data.current || !data.comparison) {
                throw new Error('Invalid comparison data structure');
            }
            
            try {
                const current = sanitizeDataForExport(data.current);
                const comparison = sanitizeDataForExport(data.comparison);
                
                // Ensure both datasets have the same shape counts
                if (JSON.stringify(current.shape_counts) !== JSON.stringify(comparison.shape_counts)) {
                    throw new Error('Shape counts in comparison data do not match');
                }
                
                return { current, comparison };
            } catch (error) {
                throw new Error(`Comparison data validation failed: ${error.message}`);
            }
        }
        
        function showExportError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'export-error';
            errorDiv.textContent = `Export Error: ${message}`;
            document.body.appendChild(errorDiv);
            setTimeout(() => errorDiv.remove(), 5000);
        }
        
        function exportData(format) {
            try {
                const data = sanitizeDataForExport(window.currentData);
                var content, filename, type;
                
                if (format === 'csv') {
                    content = 'Shape Count,Duration (ms)\\n';
                    data.shape_counts.forEach((count, i) => {
                        content += `${count},${data.durations[i]}\\n`;
                    });
                    filename = `performance_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.csv`;
                    type = 'text/csv';
                } else if (format === 'json') {
                    content = JSON.stringify(data, null, 2);
                    filename = `performance_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.json`;
                    type = 'application/json';
                } else if (format === 'excel') {
                    content = 'Shape Count\\tDuration (ms)\\n';
                    data.shape_counts.forEach((count, i) => {
                        content += `${count}\\t${data.durations[i]}\\n`;
                    });
                    filename = `performance_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.xls`;
                    type = 'application/vnd.ms-excel';
                }
                
                downloadFile(content, filename, type);
            } catch (error) {
                showExportError(error.message);
            }
        }
        
        function exportComparisonData(format) {
            try {
                const data = sanitizeComparisonDataForExport(window.comparisonData);
                var content, filename, type;
                
                if (format === 'csv') {
                    content = 'Shape Count,Current Duration (ms),Comparison Duration (ms)\\n';
                    data.current.shape_counts.forEach((count, i) => {
                        content += `${count},${data.current.durations[i]},${data.comparison.durations[i]}\\n`;
                    });
                    filename = `comparison_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.csv`;
                    type = 'text/csv';
                } else if (format === 'json') {
                    content = JSON.stringify(data, null, 2);
                    filename = `comparison_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.json`;
                    type = 'application/json';
                } else if (format === 'excel') {
                    content = 'Shape Count\\tCurrent Duration (ms)\\tComparison Duration (ms)\\n';
                    data.current.shape_counts.forEach((count, i) => {
                        content += `${count}\\t${data.current.durations[i]}\\t${data.comparison.durations[i]}\\n`;
                    });
                    filename = `comparison_data_${new Date().toISOString().slice(0,19).replace(/[:]/g, '')}.xls`;
                    type = 'application/vnd.ms-excel';
                }
                
                downloadFile(content, filename, type);
            } catch (error) {
                showExportError(error.message);
            }
        }
        
        function downloadFile(content, filename, type) {
            var blob = new Blob([content], { type: type });
            var link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);  // Clean up the URL object
        }
        
        function filterData(chartId, minValue, maxValue) {
            var chart = document.getElementById(chartId);
            var update = {
                'xaxis.range': [minValue, maxValue]
            };
            Plotly.relayout(chart, update);
        }
        
        function toggleComparison(chartId, showComparison) {
            var chart = document.getElementById(chartId);
            var update = {
                'visible': showComparison ? [true, true] : [true, false]
            };
            Plotly.restyle(chart, update);
        }
        
        function updateChartType(chartId, type) {
            var chart = document.getElementById(chartId);
            var update = {'type': type};
            Plotly.restyle(chart, update);
        }
        </script>
        """
        
        # Add export error styling
        export_error_style = """
        .export-error {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background-color: #ff4444;
            color: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: fadeInOut 5s ease-in-out;
        }
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateY(-20px); }
            10% { opacity: 1; transform: translateY(0); }
            90% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0; transform: translateY(-20px); }
        }
        """
        
        # Add export controls HTML
        export_controls = """
        <div class="export-controls">
            <h3>Export Data</h3>
            <div class="control-group">
                <label>Current Data:</label>
                <div class="button-group">
                    <button onclick="exportData('csv')" class="export-button">CSV</button>
                    <button onclick="exportData('json')" class="export-button">JSON</button>
                    <button onclick="exportData('excel')" class="export-button">Excel</button>
                </div>
            </div>
            <div class="control-group">
                <label>Comparison Data:</label>
                <div class="button-group">
                    <button onclick="exportComparisonData('csv')" class="export-button">CSV</button>
                    <button onclick="exportComparisonData('json')" class="export-button">JSON</button>
                    <button onclick="exportComparisonData('excel')" class="export-button">Excel</button>
                </div>
            </div>
        </div>
        """
        
        # Combine with existing filter controls
        filter_controls = f"""
        <div class="filter-controls">
            <div class="control-group">
                <label for="shape-count-min">Min Shape Count:</label>
                <input type="number" id="shape-count-min" value="0" 
                       onchange="filterData('duration-chart', this.value, document.getElementById('shape-count-max').value)">
            </div>
            <div class="control-group">
                <label for="shape-count-max">Max Shape Count:</label>
                <input type="number" id="shape-count-max" value="5000"
                       onchange="filterData('duration-chart', document.getElementById('shape-count-min').value, this.value)">
            </div>
            <div class="control-group">
                <label for="comparison-toggle">Show Comparison:</label>
                <input type="checkbox" id="comparison-toggle"
                       onchange="toggleComparison('duration-chart', this.checked)">
            </div>
            <div class="control-group">
                <label for="chart-type">Chart Type:</label>
                <select id="chart-type" onchange="updateChartType('duration-chart', this.value)">
                    <option value="scatter">Line + Markers</option>
                    <option value="bar">Bar</option>
                    <option value="heatmap">Heatmap</option>
                </select>
            </div>
            {export_controls}
        </div>
        """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Test Report - {timestamp}</title>
            <style>
                {export_error_style}
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ 
                    text-align: center; 
                    margin-bottom: 40px;
                    background: #fff;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metrics {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .metric-box {{ 
                    padding: 25px; 
                    background: #fff; 
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                }}
                .metric-box:hover {{
                    transform: translateY(-5px);
                }}
                .visualization {{ 
                    margin: 30px 0;
                    background: #fff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .visualization iframe {{ 
                    width: 100%;
                    height: 500px;
                    border: none;
                    border-radius: 5px;
                }}
                .recommendations {{ margin: 30px 0; }}
                .recommendation {{ 
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    background: #fff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .high {{ border-left: 4px solid #ff4444; }}
                .medium {{ border-left: 4px solid #ffbb33; }}
                .low {{ border-left: 4px solid #00C851; }}
                .system-info {{
                    background: #fff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-top: 30px;
                }}
                h1, h2, h3, h4 {{ color: #2c3e50; }}
                .success-rate {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {self._get_success_rate_color(report_data)}
                }}
                .filter-controls {{
                    background: #fff;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin: 20px 0;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                }}
                .control-group {{
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }}
                .control-group label {{
                    font-size: 14px;
                    color: #2c3e50;
                }}
                .control-group input[type="number"] {{
                    width: 100px;
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                .control-group select {{
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background: #fff;
                }}
                .export-controls {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #fff;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .export-controls h3 {{
                    margin: 0 0 15px 0;
                    color: #2c3e50;
                }}
                .button-group {{
                    display: flex;
                    gap: 10px;
                    margin-top: 5px;
                }}
                .export-button {{
                    padding: 8px 15px;
                    border: none;
                    border-radius: 4px;
                    background: #3498db;
                    color: white;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                .export-button:hover {{
                    background: #2980b9;
                }}
            </style>
            {js_code}
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Performance Test Report</h1>
                    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                {filter_controls}
                
                <div class="metrics">
                    <div class="metric-box">
                        <h3>Tests Run</h3>
                        <p style="font-size: 24px;">{report_data['test_results']['tests_run']}</p>
                    </div>
                    <div class="metric-box">
                        <h3>Success Rate</h3>
                        <p class="success-rate">
                            {(report_data['test_results']['tests_run'] - 
                              report_data['test_results']['failures']) / 
                              report_data['test_results']['tests_run'] * 100:.1f}%
                        </p>
                    </div>
                    <div class="metric-box">
                        <h3>Failed Tests</h3>
                        <p style="font-size: 24px; color: #ff4444;">
                            {report_data['test_results']['failures']}
                        </p>
                    </div>
                </div>
                
                <div class="visualizations">
                    <h2>Performance Visualizations</h2>
                    {self._generate_chart_sections(chart_files)}
                </div>
                
                <div class="recommendations">
                    <h2>Recommendations</h2>
                    {self._generate_recommendation_sections(report_data['recommendations'])}
                </div>
                
                <div class="system-info">
                    <h2>System Information</h2>
                    {self._generate_system_info_section(report_data['system_info'])}
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        return html_file
    
    def _generate_chart_sections(self, chart_files):
        """Generate HTML sections for interactive charts."""
        sections = []
        for chart_file in chart_files:
            filename = os.path.basename(chart_file)
            title = ' '.join(word.title() for word in filename.split('_')[:2])
            sections.append(f"""
                <div class="visualization">
                    <h3>{title}</h3>
                    <iframe src="{chart_file}"></iframe>
                </div>
            """)
        return '\n'.join(sections)
    
    def _generate_recommendation_sections(self, recommendations):
        """Generate HTML sections for recommendations."""
        sections = []
        for rec in recommendations:
            sections.append(f"""
                <div class="recommendation {rec['priority']}">
                    <h4>{rec['message']}</h4>
                    <p>{rec['details']}</p>
                </div>
            """)
        return '\n'.join(sections)
    
    def _generate_system_info_section(self, system_info):
        """Generate HTML section for system information."""
        items = []
        for key, value in system_info.items():
            if 'memory' in key.lower():
                value = f"{value / (1024**3):.2f} GB"
            items.append(f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>")
        return f"<ul style='list-style-type: none; padding: 0;'>{''.join(items)}</ul>"
    
    def _get_success_rate_color(self, report_data):
        """Get color for success rate based on percentage."""
        success_rate = ((report_data['test_results']['tests_run'] - 
                        report_data['test_results']['failures']) / 
                       report_data['test_results']['tests_run'] * 100)
        if success_rate >= 90:
            return '#00C851'  # Green
        elif success_rate >= 75:
            return '#ffbb33'  # Yellow
        else:
            return '#ff4444'  # Red 