import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os
import json
import logging
from typing import List, Dict, Union, Optional

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
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize validation stats
        self.validation_stats = {
            'total_validations': 0,
            'failed_validations': 0,
            'validation_errors': []
        }
    
    def _validate_data(self, shape_counts: List[int], durations: List[float], 
                      test_type: str = 'batch') -> Dict[str, List[str]]:
        """Validate input data for visualization."""
        errors = []
        warnings = []
        
        # Check for empty arrays
        if not shape_counts or not durations:
            errors.append("Empty arrays provided for shape_counts or durations")
            return {'errors': errors, 'warnings': warnings}
        
        # Check array lengths match
        if len(shape_counts) != len(durations):
            errors.append(f"Array length mismatch: shape_counts ({len(shape_counts)}) != durations ({len(durations)})")
            return {'errors': errors, 'warnings': warnings}
        
        # Validate numeric values
        for i, (count, duration) in enumerate(zip(shape_counts, durations)):
            # Check for non-numeric values
            if not isinstance(count, (int, float)):
                errors.append(f"Non-numeric value found in shape_counts at index {i}: {count}")
            if not isinstance(duration, (int, float)):
                errors.append(f"Non-numeric value found in durations at index {i}: {duration}")
            
            # Check for negative values
            if isinstance(count, (int, float)) and count < 0:
                errors.append(f"Negative shape count found at index {i}: {count}")
            if isinstance(duration, (int, float)) and duration < 0:
                errors.append(f"Negative duration found at index {i}: {duration}")
            
            # Check for NaN or Inf values
            if isinstance(count, float) and (np.isnan(count) or np.isinf(count)):
                errors.append(f"Invalid shape count (NaN/Inf) found at index {i}")
            if isinstance(duration, float) and (np.isnan(duration) or np.isinf(duration)):
                errors.append(f"Invalid duration (NaN/Inf) found at index {i}")
        
        # Performance warnings
        if len(shape_counts) > 1000:
            warnings.append(f"Large dataset detected ({len(shape_counts)} points). This may impact visualization performance.")
        
        # Update validation stats
        self.validation_stats['total_validations'] += 1
        if errors:
            self.validation_stats['failed_validations'] += 1
            self.validation_stats['validation_errors'].extend(errors)
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_comparison_data(self, current_data: Dict, comparison_data: Dict) -> Dict[str, List[str]]:
        """Validate comparison data for visualization."""
        errors = []
        warnings = []
        
        required_keys = ['shape_counts', 'durations']
        
        # Check for required keys
        for key in required_keys:
            if key not in current_data:
                errors.append(f"Missing required key '{key}' in current data")
            if key not in comparison_data:
                errors.append(f"Missing required key '{key}' in comparison data")
        
        if errors:
            return {'errors': errors, 'warnings': warnings}
        
        # Validate data types and lengths
        current_counts = current_data['shape_counts']
        current_durations = current_data['durations']
        comp_counts = comparison_data['shape_counts']
        comp_durations = comparison_data['durations']
        
        # Validate each dataset
        current_validation = self._validate_data(current_counts, current_durations)
        comp_validation = self._validate_data(comp_counts, comp_durations)
        
        errors.extend(current_validation['errors'])
        errors.extend(comp_validation['errors'])
        warnings.extend(current_validation['warnings'])
        warnings.extend(comp_validation['warnings'])
        
        # Compare datasets
        if len(current_counts) != len(comp_counts):
            warnings.append(f"Dataset size mismatch: current ({len(current_counts)}) vs comparison ({len(comp_counts)})")
        
        # Check for significant differences
        if not errors and len(current_counts) == len(comp_counts):
            count_diffs = np.array(current_counts) - np.array(comp_counts)
            duration_diffs = np.array(current_durations) - np.array(comp_durations)
            
            if np.any(np.abs(count_diffs) > 0):
                warnings.append("Shape count differences detected between current and comparison data")
            if np.any(np.abs(duration_diffs) > 1000):  # 1000ms threshold
                warnings.append("Significant duration differences detected (>1000ms)")
        
        return {'errors': errors, 'warnings': warnings}
    
    def get_validation_summary(self) -> Dict[str, Union[int, List[str]]]:
        """Get summary of validation statistics."""
        return {
            'total_validations': self.validation_stats['total_validations'],
            'failed_validations': self.validation_stats['failed_validations'],
            'error_rate': (self.validation_stats['failed_validations'] / 
                         max(1, self.validation_stats['total_validations'])),
            'recent_errors': self.validation_stats['validation_errors'][-10:]  # Last 10 errors
        }
    
    def _format_validation_messages(self, validation_results: Dict[str, List[str]]) -> str:
        """Format validation messages for display."""
        messages = []
        
        if validation_results['errors']:
            messages.append("<div class='validation-errors'>")
            messages.append("<h3>Validation Errors:</h3>")
            messages.extend([f"<p class='error-message'>{error}</p>" 
                           for error in validation_results['errors']])
            messages.append("</div>")
        
        if validation_results['warnings']:
            messages.append("<div class='validation-warnings'>")
            messages.append("<h3>Validation Warnings:</h3>")
            messages.extend([f"<p class='warning-message'>{warning}</p>" 
                           for warning in validation_results['warnings']])
            messages.append("</div>")
        
        return "\n".join(messages)
    
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
        # Validate input data
        validation_results = self._validate_data(shape_counts, durations, test_type)
        
        if validation_results['errors']:
            self.logger.error("Validation errors encountered:")
            for error in validation_results['errors']:
                self.logger.error(error)
            raise ValueError("Invalid input data. Check logs for details.")
        
        if validation_results['warnings']:
            for warning in validation_results['warnings']:
                self.logger.warning(warning)
        
        # Validate comparison data if provided
        if comparison_data:
            comp_validation = self._validate_comparison_data(
                {'shape_counts': shape_counts, 'durations': durations},
                comparison_data
            )
            if comp_validation['errors']:
                self.logger.error("Comparison data validation errors:")
                for error in comp_validation['errors']:
                    self.logger.error(error)
                raise ValueError("Invalid comparison data. Check logs for details.")
            
            if comp_validation['warnings']:
                for warning in comp_validation['warnings']:
                    self.logger.warning(warning)
        
        # Apply filters if provided
        if filters:
            try:
                filtered_indices = self._apply_filters(shape_counts, filters)
                shape_counts = [shape_counts[i] for i in filtered_indices]
                durations = [durations[i] for i in filtered_indices]
                
                if not shape_counts:
                    raise ValueError("No data points remain after applying filters")
            except Exception as e:
                self.logger.error(f"Error applying filters: {str(e)}")
                raise
        
        # Create figure based on comparison mode
        try:
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
            
            # Add validation messages to the plot
            validation_html = self._format_validation_messages({
                'errors': validation_results['errors'],
                'warnings': validation_results['warnings']
            })
            
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
                window.validationSummary = {json.dumps(self.get_validation_summary())};
                </script>
                
                <style>
                .validation-errors, .validation-warnings {{
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 4px;
                }}
                .validation-errors {{
                    background-color: #ffebee;
                    border: 1px solid #ffcdd2;
                }}
                .validation-warnings {{
                    background-color: #fff3e0;
                    border: 1px solid #ffe0b2;
                }}
                .error-message {{
                    color: #c62828;
                    margin: 5px 0;
                }}
                .warning-message {{
                    color: #ef6c00;
                    margin: 5px 0;
                }}
                </style>
                
                {validation_html}
                """
            else:
                js_data = f"""
                <script>
                window.currentData = {{
                    shape_counts: {json.dumps(shape_counts)},
                    durations: {json.dumps(durations)}
                }};
                window.comparisonData = null;
                window.validationSummary = {json.dumps(self.get_validation_summary())};
                </script>
                
                <style>
                .validation-errors, .validation-warnings {{
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 4px;
                }}
                .validation-errors {{
                    background-color: #ffebee;
                    border: 1px solid #ffcdd2;
                }}
                .validation-warnings {{
                    background-color: #fff3e0;
                    border: 1px solid #ffe0b2;
                }}
                .error-message {{
                    color: #c62828;
                    margin: 5px 0;
                }}
                .warning-message {{
                    color: #ef6c00;
                    margin: 5px 0;
                }}
                </style>
                
                {validation_html}
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
            
            self.logger.info(f"Generated performance visualization: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Error generating performance visualization: {str(e)}")
            raise
    
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