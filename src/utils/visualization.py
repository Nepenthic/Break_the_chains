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
    
    def generate_html_report(self, test_data, chart_files):
        """Generate an HTML report with interactive visualizations and export functionality."""
        # Add CSS for progress indicator and status messages
        css = """
            .progress-container {
                width: 100%;
                margin: 10px 0;
                display: none;
            }
            .progress-bar {
                width: 0%;
                height: 4px;
                background-color: #4CAF50;
                transition: width 0.3s ease-in-out;
            }
            .status-message {
                margin: 5px 0;
                padding: 8px;
                border-radius: 4px;
                display: none;
            }
            .status-success {
                background-color: #E8F5E9;
                color: #2E7D32;
                border: 1px solid #A5D6A7;
            }
            .status-error {
                background-color: #FFEBEE;
                color: #C62828;
                border: 1px solid #FFCDD2;
            }
            .status-warning {
                background-color: #FFF3E0;
                color: #EF6C00;
                border: 1px solid #FFE0B2;
            }
            .status-info {
                background-color: #E3F2FD;
                color: #1565C0;
                border: 1px solid #90CAF9;
            }
        """

        # Add JavaScript for progress and status handling
        js = """
            function showProgress(show = true) {
                document.querySelector('.progress-container').style.display = show ? 'block' : 'none';
            }

            function updateProgress(percent) {
                document.querySelector('.progress-bar').style.width = `${percent}%`;
            }

            function showStatus(message, type = 'info') {
                const statusEl = document.querySelector('.status-message');
                statusEl.textContent = message;
                statusEl.className = `status-message status-${type}`;
                statusEl.style.display = 'block';
                
                // Auto-hide success messages after 3 seconds
                if (type === 'success') {
                    setTimeout(() => {
                        statusEl.style.display = 'none';
                    }, 3000);
                }
            }

            async function exportData(format) {
                showProgress();
                showStatus('Preparing data for export...', 'info');
                
                try {
                    // Validate data
                    updateProgress(20);
                    const validationResult = validateDataArrays(window.currentData.shape_counts, window.currentData.durations);
                    if (!validationResult.isValid) {
                        throw new Error(validationResult.error);
                    }
                    
                    // Sanitize data
                    updateProgress(40);
                    const sanitizedData = sanitizeDataForExport(window.currentData);
                    
                    // Format data
                    updateProgress(60);
                    let exportContent;
                    let filename;
                    const timestamp = new Date().toISOString().slice(0,19).replace(/[:-]/g, '');
                    
                    switch(format) {
                        case 'csv':
                            exportContent = formatCSV(sanitizedData);
                            filename = `performance_data_${timestamp}.csv`;
                            break;
                        case 'json':
                            exportContent = formatJSON(sanitizedData);
                            filename = `performance_data_${timestamp}.json`;
                            break;
                        case 'excel':
                            exportContent = formatExcel(sanitizedData);
                            filename = `performance_data_${timestamp}.xls`;
                            break;
                        default:
                            throw new Error(`Unsupported format: ${format}`);
                    }
                    
                    // Create and trigger download
                    updateProgress(80);
                    const blob = new Blob([exportContent], { type: getMimeType(format) });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    updateProgress(100);
                    showStatus(`Data exported successfully as ${format.toUpperCase()}`, 'success');
                } catch (error) {
                    showStatus(error.message, 'error');
                } finally {
                    setTimeout(() => {
                        showProgress(false);
                        updateProgress(0);
                    }, 1000);
                }
            }

            async function exportComparisonData(format) {
                showProgress();
                showStatus('Preparing comparison data for export...', 'info');
                
                try {
                    // Validate both datasets
                    updateProgress(20);
                    const currentValidation = validateDataArrays(window.currentData.shape_counts, window.currentData.durations);
                    const comparisonValidation = validateDataArrays(window.comparisonData.shape_counts, window.comparisonData.durations);
                    
                    if (!currentValidation.isValid || !comparisonValidation.isValid) {
                        throw new Error('Invalid data in current or comparison dataset');
                    }
                    
                    // Validate matching shape counts
                    if (!arraysMatch(window.currentData.shape_counts, window.comparisonData.shape_counts)) {
                        throw new Error('Shape counts in current and comparison data do not match');
                    }
                    
                    // Sanitize both datasets
                    updateProgress(40);
                    const sanitizedCurrent = sanitizeDataForExport(window.currentData);
                    const sanitizedComparison = sanitizeDataForExport(window.comparisonData);
                    
                    // Format data
                    updateProgress(60);
                    let exportContent;
                    let filename;
                    const timestamp = new Date().toISOString().slice(0,19).replace(/[:-]/g, '');
                    
                    switch(format) {
                        case 'csv':
                            exportContent = formatComparisonCSV(sanitizedCurrent, sanitizedComparison);
                            filename = `comparison_data_${timestamp}.csv`;
                            break;
                        case 'json':
                            exportContent = formatComparisonJSON(sanitizedCurrent, sanitizedComparison);
                            filename = `comparison_data_${timestamp}.json`;
                            break;
                        case 'excel':
                            exportContent = formatComparisonExcel(sanitizedCurrent, sanitizedComparison);
                            filename = `comparison_data_${timestamp}.xls`;
                            break;
                        default:
                            throw new Error(`Unsupported format: ${format}`);
                    }
                    
                    // Create and trigger download
                    updateProgress(80);
                    const blob = new Blob([exportContent], { type: getMimeType(format) });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    updateProgress(100);
                    showStatus(`Comparison data exported successfully as ${format.toUpperCase()}`, 'success');
                } catch (error) {
                    showStatus(error.message, 'error');
                } finally {
                    setTimeout(() => {
                        showProgress(false);
                        updateProgress(0);
                    }, 1000);
                }
            }
        """

        # Generate HTML content
        html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Performance Test Report</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <style>{css}</style>
            </head>
            <body>
                <div class="container mt-4">
                    <h1 class="mb-4">Performance Test Report</h1>
                    
                    <!-- Progress and Status -->
                    <div class="progress-container">
                        <div class="progress-bar"></div>
                    </div>
                    <div class="status-message"></div>
                    
                    <!-- Export Controls -->
                    <div class="export-controls mb-4">
                        <h3>Export Options</h3>
                        <div class="button-group">
                            <button onclick="exportData('csv')" class="btn btn-primary">Export as CSV</button>
                            <button onclick="exportData('json')" class="btn btn-primary">Export as JSON</button>
                            <button onclick="exportData('excel')" class="btn btn-primary">Export as Excel</button>
                        </div>
                        
                        {{% if has_comparison_data %}}
                        <div class="button-group mt-2">
                            <button onclick="exportComparisonData('csv')" class="btn btn-secondary">Export Comparison as CSV</button>
                            <button onclick="exportComparisonData('json')" class="btn btn-secondary">Export Comparison as JSON</button>
                            <button onclick="exportComparisonData('excel')" class="btn btn-secondary">Export Comparison as Excel</button>
                        </div>
                        {{% endif %}}
                    </div>
                    
                    <!-- Test Results -->
                    {self._generate_test_results_section(test_data)}
                    
                    <!-- Charts -->
                    {self._generate_chart_sections(chart_files)}
                    
                    <!-- System Info -->
                    {self._generate_system_info_section(test_data.get('system_info', {}))}
                    
                    <!-- Recommendations -->
                    {self._generate_recommendation_sections(test_data.get('recommendations', []))}
                </div>
                
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
                <script>{js}</script>
            </body>
            </html>
        """

        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.output_dir, f'performance_report_{timestamp}.html')
        with open(report_file, 'w') as f:
            f.write(html)
        
        return report_file
    
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