import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State, MATCH, ALL
from math import log10, floor
import numpy as np
from profit.util import load
from profit.sur import Surrogate
from matplotlib import cm as colormaps
from matplotlib.colors import to_hex as color2hex

def init_app(config):
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
    external_scripts = ['https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.4/MathJax.js?config=TeX-MML-AM_CHTML']

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets, external_scripts=external_scripts)
    server = app.server
    app.config.suppress_callback_exceptions = False

    indata = load(config['files']['input']).flatten()
    outdata = load(config['files']['output']).flatten()

    # data = pd.concat([indata, outdata], 1) # TODO: data in table

    invars = indata.dtype.names
    outvars = outdata.dtype.names
    dd_opts_in = [{'label': invar, 'value': invar} for invar in invars]
    dd_opts_out = [{'label': outvar, 'value': outvar} for outvar in outvars]

    col_width = 400
    txt_width = 100
    dd_width = 250
    log_width = 50
    graph_height = 620
    txt_check_width = 50
    check_txt_width = txt_width-txt_check_width
    ax_opt_tit_sty = {'width': col_width}
    ax_opt_txt_sty = {'width': txt_width}
    ax_opt_log_sty = {'width': log_width}
    dd_sty = {'width': dd_width}
    axis_options_div_style = {'display': 'flex', 'align-items': 'center', 'height':36, 'padding': 1}
    fit_opt_txt_sty = {'width': txt_width}
    headline_sty = {'text-align': 'center', 'display': 'block', 'width': col_width-25}

    def colormap(cmin, cmax, c):
        if cmin == cmax:
            c_scal = 0.5
        else:
            c_scal = (c-cmin)/(cmax-cmin)
        return color2hex(colormaps.cividis(c_scal))

    app.layout = html.Div(children=[
        html.Table(children=[html.Tr(children=[
            html.Td(id='axis-options', style={'width': '20%'}, children=[
                html.Div(dcc.RadioItems(
                    id='graph-type',
                    options=[{'label': i, 'value': i} for i in ['1D', '2D', '2D contour', '3D']],
                    value='1D',
                    labelStyle={'display': 'inline-block'})),
                html.Div(id='header-opt', children=[html.B("Axis options:", style=headline_sty)], style=ax_opt_tit_sty),
                html.Div(id='invar-1-div', style=axis_options_div_style, children=[
                    html.B('x: ', style=ax_opt_txt_sty),
                    dcc.Dropdown(id='invar', options=dd_opts_in, value=invars[0], style=dd_sty),
                    dcc.Checklist(id='invar-1-log', options=[{'label': 'log', 'value': 'log'}], style=ax_opt_log_sty),
                ]),
                html.Div(id='invar-2-div', style=axis_options_div_style, children=[
                    html.B('y: ', style=ax_opt_txt_sty),
                    dcc.Dropdown(
                        id='invar_2',
                        options=dd_opts_in,
                        value=invars[1] if len(invars) > 1 else invars[0],
                        style=dd_sty, ),
                    dcc.Checklist(
                        id='invar-2-log',
                        options=[{'label': 'log', 'value': 'log'}],
                        style=ax_opt_log_sty, ),
                ]),
                html.Div(id='invar-3-div', style=axis_options_div_style, children=[
                    html.B('z: ', style=ax_opt_txt_sty),
                    dcc.Dropdown(
                        id='invar_3',
                        options=dd_opts_in,
                        value=invars[2] if len(invars) > 2 else invars[0],
                        style=dd_sty,
                    ),
                    dcc.Checklist(
                        id='invar-3-log',
                        options=[{'label': 'log', 'value': 'log'}],
                        style=ax_opt_log_sty,
                    ),
                ]),
                html.Div(id='outvar-div', style=axis_options_div_style, children=[
                    html.B('output: ', style=ax_opt_txt_sty),
                    dcc.Dropdown(
                        id='outvar',
                        options=dd_opts_out,
                        value=outvars[0],
                        style=dd_sty, ),
                    dcc.Checklist(
                        id='outvar-log',
                        options=[{'label': 'log', 'value': 'log'}],
                        style=ax_opt_log_sty, ),
                ]),
                html.Div(id='color-div', style=axis_options_div_style, children=[
                    html.B("color: ", style={'width': txt_check_width}),
                    dcc.Checklist(
                        id='color-use',
                        options=[{'label': '', 'value': 'true'}],
                        style={'width': check_txt_width}, ),
                    dcc.Dropdown(
                        id='color-dropdown',
                        options=dd_opts_in + dd_opts_out,
                        value=invars[2] if len(invars) > 2 else invars[0],
                        style=dd_sty, ),
                ]),
                html.Div(id='error-div', style=axis_options_div_style, children=[
                    html.B("error: ", style={'width': txt_check_width}),
                    dcc.Checklist(
                        id='error-use',
                        options=[{'label': '', 'value': 'true'}],
                        style={'width': check_txt_width}, ),
                    dcc.Dropdown(
                        id='error-dropdown',
                        options=dd_opts_out,
                        value=outvars[-1],
                        style=dd_sty, ),
                ]),
                html.Div(id='fit-opt', children=html.B("Fit options:", style=headline_sty), style=ax_opt_tit_sty),
                html.Div(id='fit-use-div', style=axis_options_div_style, children=[
                    html.B("display fit:", style=fit_opt_txt_sty),
                    dcc.Checklist(
                        id='fit-use',
                        options=[{'label': '', 'value': 'show'}],
                        labelStyle={'display': 'inline-block'}, ),
                ]),
                html.Div(id='fit-multiinput-div', style=axis_options_div_style, children=[
                    html.B("multi-fit:", style=fit_opt_txt_sty),
                    dcc.Dropdown(
                        id='fit-multiinput-dropdown',
                        options=dd_opts_in,
                        value=invars[-1],
                        style=dd_sty, ),
                ]),
                html.Div(id='fit-number-div', style=axis_options_div_style, children=[
                    html.B("#fits:", style=fit_opt_txt_sty),
                    dcc.Input(id='fit-number', type='number', value=1, min=1),
                ]),
                html.Div(id='fit-conf-div', style=axis_options_div_style, children=[
                    html.B("\u03c3-confidence:", style=fit_opt_txt_sty),
                    dcc.Input(id='fit-conf', type='number', value=2, min=0),
                ]),
                html.Div(id='fit-noise-div', style=axis_options_div_style, children=[
                    dcc.Checklist(
                        id='fit-var',
                        options=[{'label': 'add noise covariance', 'value': 'add'}],
                        style={'margin-left': txt_width},
                    )
                ]),
                html.Div(id='fit-color-div', style=axis_options_div_style, children=[
                    html.B("fit-color:", style=fit_opt_txt_sty),
                    dcc.RadioItems(
                        id='fit-color',
                        options=[{'label': 'output', 'value': 'output'},
                                 {'label': 'variable of multi-fit', 'value': 'multi-fit'}],
                        value='output',
                        labelStyle={'display': 'inline-block'}, ),
                ]),
                html.Div(id='fit-opacity-div', style=axis_options_div_style, children=[
                    html.B("fit-opacity:", style=fit_opt_txt_sty),
                    html.Div(style={'width': col_width-txt_width}, children=[
                        dcc.Slider(
                            id='fit-opacity',
                            min=0,
                            max=1,
                            step=0.1,
                            value=0.5,
                            marks={i: {'label': f'{100 * i:.0f}%'} for i in [0, 0.2, 0.4, 0.6, 0.8, 1]},
                        ),
                    ]),
                ]),
                html.Div(id='fit-sampling-div', style=axis_options_div_style, children=[
                    html.B("#sampling:", style=fit_opt_txt_sty),
                    dcc.Input(id='fit-sampling', type='number', value=50, min=20, max=100),
                ]),
            ]),
            html.Td(id='graph', style={'width': '80%'}, children=[html.Div(dcc.Graph(id='graph1'))]),
        ])]),
        html.Div(html.Table(id='filters', children=[html.Tr([
            html.Td(html.Div([
                dcc.Dropdown(
                    id='filter-dropdown',
                    options=dd_opts_in,
                    value=invars[0],
                    style={'width': 200, 'margin-right': 10},
                ),
                html.Button("Add Filter", id='add-filter', n_clicks=0),
            ], style={'display': 'flex'})),
            html.Td(html.Button("Clear Filter", id='clear-filter', n_clicks=0)),
            html.Td(html.Button("Clear all Filter", id='clear-all-filter', n_clicks=0)),
            html.Td(dcc.Slider(id='scale-slider',
                               min=-0.5, max=0.5,
                               value=0, step=0.01,
                               marks={-1: '-100%',
                                      -0.75: '-75%',
                                      -0.5: '-50%',
                                      -0.25: '-25%',
                                      0: '0%',
                                      0.25: '25%',
                                      0.5: '50%',
                                      0.75: '75%',
                                      1: '100%'}
                               ),
                    style={'width': 500}),
            html.Td(html.Button("Scale Filter span", id='scale', n_clicks=0)),
        ])])),
        html.Div(html.Table(id='param-table', children=[
            html.Thead(id='param-table-head', children=[
                html.Tr(children=[
                    html.Th("Parameter", style={'width': 150}),
                    html.Th("Slider", style={'width': 300}),
                    html.Th("Range (min/max)"),
                    html.Th("center/span"),
                    html.Th("filter active"),
                ]),
            ]),
            html.Tbody(id='param-table-body', children=[
                html.Tr(children=[
                    html.Td(html.Div(id='param-text-div', children=[])),
                    html.Td(html.Div(id='param-slider-div', children=[])),
                    html.Td(html.Div(id='param-range-div', children=[])),
                    html.Td(html.Div(id='param-center-div', children=[])),
                    html.Td(html.Div(id='param-active-div', children=[])),
                ]),
            ]),
        ])),
        html.Div(id='data-table', children=[
            html.Div(children=[
                html.B("Show table of data:"),
                html.Button("show table", id='show-table', n_clicks=0),
                html.Button("hide table", id='hide-table', n_clicks=0),
            ], style={'visibility': 'hidden'}),
            html.Div(id='data-table-div', style={'visibility': 'hidden'}, children=[
                # dash_table.DataTable(
                #     id='data-table',
                #     columns=[{"name": i, "id": i} for i in invars],
                #     data=indata.to_dict('records'),
                #     page_size=20,
                # ) # TODO: fix table
            ])
        ]),
    ])


    @app.callback(
        [Output('param-text-div', 'children'),
         Output('param-slider-div', 'children'),
         Output('param-range-div', 'children'),
         Output('param-center-div', 'children'),
         Output('param-active-div', 'children'), ],
        [Input('add-filter', 'n_clicks'),
         Input('clear-filter', 'n_clicks'),
         Input('clear-all-filter', 'n_clicks')],
        [State('filter-dropdown', 'value'),
         State('param-text-div', 'children'),
         State('param-slider-div', 'children'),
         State('param-range-div', 'children'),
         State('param-center-div', 'children'),
         State('param-active-div', 'children'), ],
    )
    def add_filterrow(n_clicks, clear, clear_all, filter_dd, text, slider, range_div, center_div, active_div):
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == 'clear-all-filter':
            return [], [], [], [], []
        elif trigger_id == 'clear-filter':
            for i, element in enumerate(text):  # TODO: better names
                if text[i]['props']['children'][0] == filter_dd:
                    text.pop(i)
                    slider.pop(i)
                    range_div.pop(i)
                    center_div.pop(i)
                    active_div.pop(i)
        elif trigger_id == 'add-filter':  # TODO: avoid double usage of filter
            for i, element in enumerate(text):
                if text[i]['props']['children'][0] == filter_dd:
                    return text, slider, range_div, center_div, active_div
            ind = invars.index(filter_dd)
            txt = filter_dd
            new_text = html.Div(id={'type': 'dyn-text', 'index': ind}, children=[txt], style={'height': 40})
            new_slider = html.Div(id={'type': 'dyn-slider', 'index': ind}, style={'height': 40}, children=[
                create_slider(txt)], )
            new_range = html.Div(id={'type': 'dyn-range', 'index': ind}, style={'height': 40}, children=[
                dcc.Input(id={'type': 'param-range-min', 'index': ind}, type='number', placeholder='range min'),
                dcc.Input(id={'type': 'param-range-max', 'index': ind}, type='number', placeholder='range max'),
            ], )
            new_center = html.Div(id={'type': 'dyn-center', 'index': ind}, style={'height': 40}, children=[
                dcc.Input(id={'type': 'param-center', 'index': ind}, type='number', placeholder='center'),
                dcc.Input(id={'type': 'param-span', 'index': ind}, type='number', placeholder='span'),
            ], )
            new_active = html.Div(id={'type': 'dyn-active', 'index': ind},
                                  style={'height': 40, 'text-align': 'center'},
                                  children=[
                                      dcc.Checklist(id={'type': 'param-active', 'index': ind},
                                                    options=[{'label': '', 'value': 'act'}],
                                                    value=['act'],
                                                    )
                                  ])
            text.append(new_text)
            slider.append(new_slider)
            range_div.append(new_range)
            center_div.append(new_center)
            active_div.append(new_active)
        return text, slider, range_div, center_div, active_div


    @app.callback(
        [Output({'type': 'param-range-min', 'index': MATCH}, 'step'),
         Output({'type': 'param-range-max', 'index': MATCH}, 'step'),
         Output({'type': 'param-center', 'index': MATCH}, 'step'),
         Output({'type': 'param-span', 'index': MATCH}, 'step'), ],
        Input({'type': 'param-slider', 'index': MATCH}, 'step')
    )
    def update_step(step):
        return step, step, step, step


    @app.callback(
        [Output({'type': 'param-range-min', 'index': MATCH}, 'value'),
         Output({'type': 'param-range-max', 'index': MATCH}, 'value'),
         Output({'type': 'param-slider', 'index': MATCH}, 'value'),
         Output({'type': 'param-center', 'index': MATCH}, 'value'),
         Output({'type': 'param-span', 'index': MATCH}, 'value'), ],
        [Input({'type': 'param-range-min', 'index': MATCH}, 'value'),
         Input({'type': 'param-range-max', 'index': MATCH}, 'value'),
         Input({'type': 'param-slider', 'index': MATCH}, 'value'),
         Input({'type': 'param-center', 'index': MATCH}, 'value'),
         Input({'type': 'param-span', 'index': MATCH}, 'value'),
         Input('scale', 'n_clicks'), ],
        [State({'type': 'param-slider', 'index': MATCH}, 'step'),
         State('scale-slider', 'value'), ]
    )
    def update_dyn_slider_range(dyn_min, dyn_max, slider_val, center, span, scale, step, scale_slider):
        ctx = dash.callback_context
        # print(ctx.triggered[0]["prop_id"])
        if ctx.triggered[0]["prop_id"] == "scale.n_clicks":
            span = span * (1 + scale_slider)
            dyn_min = center - span
            dyn_max = center + span
            slider_val = [dyn_min, dyn_max]
        else:
            trigger_id = ctx.triggered[0]["prop_id"].split('}')[0].split(',')[1].split(':')[1]
            # TODO: search in str instead of split
            if trigger_id == '"param-center"' or trigger_id == '"param-span"' and (center and span):
                # print('center')
                dyn_min = center - span
                dyn_max = center + span
                slider_val = [dyn_min, dyn_max]
            elif (trigger_id == '"param-range-min"' or trigger_id == '"param-range-max"') and (
                    dyn_min is not None and dyn_max is not None):
                # print('range')
                # print('min:', dyn_min, 'max:', dyn_max)
                slider_val = [dyn_min, dyn_max]
                span = (slider_val[1] - slider_val[0]) / 2
                center = slider_val[0] + span
            elif slider_val:
                # print('else')
                dyn_min = slider_val[0]
                dyn_max = slider_val[1]
                span = (slider_val[1] - slider_val[0]) / 2
                center = slider_val[0] + span
            # rounding based on stepsize of slider
        dig = int(-log10(step))
        slider_val = [round(slider_val[0], dig), round(slider_val[1], dig)]
        return round(dyn_min, dig), round(dyn_max, dig), slider_val, round(center, dig), round(span, dig)


    def create_slider(dd_value):
        ind = invars.index(dd_value)
        slider_min = indata[dd_value].min()
        slider_max = indata[dd_value].max()
        step_exponent = floor(log10((slider_max - slider_min) / 100))
        while slider_max / (10 ** step_exponent) > 1000:
            step_exponent = step_exponent + 1
        while (slider_max - slider_min) / (10 ** step_exponent) < 20:  # minimum of 20 steps per slider
            step_exponent = step_exponent - 1
        new_slider = dcc.RangeSlider(
            id={'type': 'param-slider', 'index': ind},
            step=10 ** step_exponent,  # floor and log10 from package `math`
            min=slider_min,
            max=slider_max,
            value=[slider_min, slider_max],
            marks={slider_min: str(round(slider_min, -step_exponent)),
                   slider_max: str(round(slider_max, -step_exponent))},
        )
        return new_slider


    @app.callback(
        [Output('invar-2-div', 'style'),
         Output('invar-3-div', 'style'),
         Output('color-div', 'style'),
         Output('fit-use-div', 'style'),
         Output('fit-multiinput-div', 'style'),
         Output('fit-number-div', 'style'),
         Output('fit-conf-div', 'style'),
         Output('fit-color-div', 'style'),
         Output('fit-opacity-div', 'style'), ],
        [Input('graph-type', 'value'), ]
    )
    def div_visibility(graph_type):
        hide = axis_options_div_style.copy()
        hide['visibility'] = 'hidden'
        show = axis_options_div_style.copy()
        show['visibility'] = 'visible'
        if graph_type == '1D':
            return hide, hide, show, show, show, show, show, hide, show
        if graph_type == '2D':
            if len(invars) <= 2:
                return show, hide, show, show, hide, hide, show, show, show
            else:
                return show, hide, show, show, show, show, show, show, show
        if graph_type == '2D contour':
            return show, hide, show, hide, hide, hide, hide, hide, hide
        if graph_type == '3D':
            return show, show, hide, show, hide, show, hide, hide, show
        else:
            return show, show, show, show, show, show, show, show, show


    @app.callback(
        Output('graph1', 'figure'),
        [Input('invar', 'value'),
         Input('invar_2', 'value'),
         Input('invar_3', 'value'),
         Input('outvar', 'value'),
         Input('invar-1-log', 'value'),
         Input('invar-2-log', 'value'),
         Input('invar-3-log', 'value'),
         Input('outvar-log', 'value'),
         Input({'type': 'param-slider', 'index': ALL}, 'value'),
         Input('graph-type', 'value'),
         Input('color-use', 'value'),
         Input('color-dropdown', 'value'),
         Input('error-use', 'value'),
         Input('error-dropdown', 'value'),
         Input({'type': 'param-active', 'index': ALL}, 'value'),
         Input('fit-use', 'value'),
         Input('fit-multiinput-dropdown', 'value'),
         Input('fit-number', 'value'),
         Input('fit-conf', 'value'),
         Input('fit-var', 'value'),
         Input('fit-color', 'value'),
         Input('fit-opacity', 'value'),
         Input('fit-sampling', 'value'), ],
        [State({'type': 'param-slider', 'index': ALL}, 'id'),
         State({'type': 'param-center', 'index': ALL}, 'value')],
    )
    def update_figure(invar, invar_2, invar_3, outvar, invar1_log, invar2_log, invar3_log, outvar_log, param_slider,
                      graph_type, color_use, color_dd, error_use, error_dd, filter_active, fit_use, fit_dd, fit_num, fit_conf, add_noise_var, fit_color,
                      fit_opacity, fit_sampling, id_type, param_center):
        if invar is None:
            return go.Figure()
        sel_y = np.full((len(outdata),), True)
        for iteration, values in enumerate(param_slider):
            dds_value = invars[id_type[iteration]['index']]
            # filter for minimum
            sel_y_min = np.array(indata[dds_value] >= param_slider[iteration][0])
            # filter for maximum
            sel_y_max = np.array(indata[dds_value] <= param_slider[iteration][1])
            # print('iter ', iteration, 'filer', filter_active[iteration][0])
            if filter_active != [[]]:
                if filter_active[iteration] == ['act']:
                    sel_y = sel_y_min & sel_y_max & sel_y
        if graph_type == '1D':
            fig = go.Figure(
                data=[go.Scatter(
                    x=indata[invar][sel_y],
                    y=outdata[outvar][sel_y],
                    mode='markers',
                    name='data',
                    error_y=dict(type='data', array=outdata[error_dd][sel_y], visible= error_use == ['true'])
                )],
                layout=go.Layout(xaxis=dict(title=invar, rangeslider=dict(visible=True)), yaxis=dict(title=outvar))
            )
            if fit_use == ['show']:
                mesh_in, mesh_out, mesh_out_std, fit_dd_values = mesh_fit(param_slider, id_type, fit_dd, fit_num,
                                                                          param_center, [invar], [invar1_log],
                                                                          outvar, fit_sampling, add_noise_var)
                for i in range(len(fit_dd_values)):
                    fig.add_trace(go.Scatter(
                        x=mesh_in[i][invars.index(invar)],
                        y=mesh_out[i],
                        mode='lines',
                        name=f'fit: {fit_dd}={fit_dd_values[i]:.1e}',
                        line_color=colormap(indata[fit_dd].min(), indata[fit_dd].max(), fit_dd_values[i]),
                        marker_line=dict(coloraxis="coloraxis2"),
                    ))
                    fig.add_trace(go.Scatter(
                        x=np.hstack((mesh_in[i][invars.index(invar)], mesh_in[i][invars.index(invar)][::-1])),
                        y=np.hstack((mesh_out[i] + fit_conf * mesh_out_std[i], mesh_out[i][::-1] - fit_conf * mesh_out_std[i][::-1])),
                        showlegend=False,
                        fill='toself',
                        line_color=colormap(indata[fit_dd].min(), indata[fit_dd].max(), fit_dd_values[i]),
                        marker_line=dict(coloraxis="coloraxis2"),
                        opacity=fit_opacity,
                    ))
        elif graph_type == '2D':
            fig = go.Figure(
                data=[go.Scatter3d(
                    x=indata[invar][sel_y],
                    y=indata[invar_2][sel_y],
                    z=outdata[outvar][sel_y],
                    mode='markers',
                    name='Data',
                    error_z=dict(type='data', array=outdata[error_dd][sel_y], visible=error_use == ['true'])
                )],
                layout=go.Layout(scene=dict(xaxis_title=invar, yaxis_title=invar_2, zaxis_title=outvar))
            )
            if fit_use == ['show'] and invar != invar_2:
                mesh_in, mesh_out, mesh_out_std, fit_dd_values = mesh_fit(param_slider, id_type, fit_dd, fit_num,
                                                                          param_center, [invar, invar_2],
                                                                          [invar1_log, invar2_log], outvar,
                                                                          fit_sampling, add_noise_var)
                for i in range(len(fit_dd_values)):
                    fig.add_trace(go.Surface(
                        x=mesh_in[i][invars.index(invar)].reshape((fit_sampling, fit_sampling)),
                        y=mesh_in[i][invars.index(invar_2)].reshape((fit_sampling, fit_sampling)),
                        z=mesh_out[i].reshape((fit_sampling, fit_sampling)),
                        name=f'fit: {fit_dd}={fit_dd_values[i]:.2f}',
                        surfacecolor=mesh_out[i].reshape((fit_sampling, fit_sampling)) if fit_color == 'output' else
                        fit_dd_values[i] * np.ones([fit_sampling, fit_sampling]),
                        opacity=fit_opacity,
                        coloraxis="coloraxis2",
                        showlegend=True,
                    ))
                    if fit_conf > 0:
                        fig.add_trace(go.Surface(
                            x=mesh_in[i][invars.index(invar)].reshape((fit_sampling, fit_sampling)),
                            y=mesh_in[i][invars.index(invar_2)].reshape((fit_sampling, fit_sampling)),
                            z=mesh_out[i].reshape((fit_sampling, fit_sampling)) + fit_conf * mesh_out_std[i].reshape((fit_sampling, fit_sampling)),
                            showlegend=False,
                            name=f'fit+v: {fit_dd}={fit_dd_values[i]:.2f}',
                            surfacecolor=mesh_out[i].reshape((fit_sampling, fit_sampling)) if fit_color == 'output' else
                            fit_dd_values[i] * np.ones([fit_sampling, fit_sampling]),
                            opacity=fit_opacity,
                            coloraxis="coloraxis2",
                        ))
                        fig.add_trace(go.Surface(
                            x=mesh_in[i][invars.index(invar)].reshape((fit_sampling, fit_sampling)),
                            y=mesh_in[i][invars.index(invar_2)].reshape((fit_sampling, fit_sampling)),
                            z=mesh_out[i].reshape((fit_sampling, fit_sampling)) - fit_conf * mesh_out_std[i].reshape((fit_sampling, fit_sampling)),
                            showlegend=False,
                            name=f'fit-v: {fit_dd}={fit_dd_values[i]:.2f}',
                            surfacecolor=mesh_out[i].reshape((fit_sampling, fit_sampling)) if fit_color == 'output' else
                            fit_dd_values[i] * np.ones([fit_sampling, fit_sampling]),
                            opacity=fit_opacity,
                            coloraxis="coloraxis2",
                        ))
                fig.update_layout(coloraxis2=dict(
                    colorbar=dict(title=outvar if fit_color == 'output' else fit_dd),
                    cmin=min(fit_dd_values) if fit_color == 'multi-fit' else None,
                    cmax=max(fit_dd_values) if fit_color == 'multi-fit' else None,
                ))
        elif graph_type == '2D contour':
            mesh_in, mesh_out, mesh_out_std, fit_dd_values = mesh_fit(param_slider, id_type, fit_dd, fit_num,
                                                                      param_center, [invar, invar_2],
                                                                      [invar1_log, invar2_log], outvar,
                                                                      fit_sampling, add_noise_var)
            fig= go.Figure()
            fig.add_trace(go.Scatter(
                x=indata[invar][sel_y],
                y=indata[invar_2][sel_y],
                mode='markers',
                name='Data',
            ))
            fig.add_trace(go.Contour(
                x=mesh_in[0][invars.index(invar)],
                y=mesh_in[0][invars.index(invar_2)],
                z=mesh_out[0],
                contours_coloring='heatmap',
                contours_showlabels=True,
                coloraxis='coloraxis2',
                name='fit',
            ))
            fig.update_xaxes(range=[log10(min(fig.data[1]['x'])), log10(max(fig.data[1]['x']))] if invar1_log == ['log']
            else [min(fig.data[1]['x']), max(fig.data[1]['x'])])
            fig.update_yaxes(range=[log10(min(fig.data[1]['y'])), log10(max(fig.data[1]['y']))] if invar2_log == ['log']
            else [min(fig.data[1]['y']), max(fig.data[1]['y'])])
            fig.update_layout(xaxis_title=invar,
                              yaxis_title=invar_2,
                              coloraxis2=dict(colorbar=dict(title=outvar),
                                              colorscale='solar',
                                              cmin=min(fig.data[1]['z']),
                                              cmax=max(fig.data[1]['z'])))
        elif graph_type == '3D':
            fig = go.Figure(
                data=go.Scatter3d(
                    x=indata[invar][sel_y],
                    y=indata[invar_2][sel_y],
                    z=indata[invar_3][sel_y],
                    mode='markers',
                    marker=dict(
                            color=outdata[outvar][sel_y],
                            coloraxis="coloraxis2",
                        ),
                    name='Data',
                ),
                layout=go.Layout(scene=dict(xaxis_title=invar, yaxis_title=invar_2, zaxis_title=invar_3)),
            )
            fig.update_layout(coloraxis2=dict(
                colorbar=dict(title=outvar),
            ))
            if fit_use == ['show'] and len({invar, invar_2, invar_3}) == 3:
                mesh_in, mesh_out, mesh_out_std, fit_dd_values = mesh_fit(param_slider, id_type, fit_dd, fit_num,
                                                                          param_center, [invar, invar_2, invar_3],
                                                                          [invar1_log, invar2_log, invar3_log], outvar,
                                                                          fit_sampling, add_noise_var)
                for i in range(len(fit_dd_values)):
                    fig.add_trace(
                        go.Isosurface(
                            x=mesh_in[i][invars.index(invar)],
                            y=mesh_in[i][invars.index(invar_2)],
                            z=mesh_in[i][invars.index(invar_3)],
                            value=mesh_out[i],
                            surface_count=fit_num,
                            coloraxis="coloraxis2",
                            isomin=mesh_out[i].min() * 1.1,
                            isomax=mesh_out[i].max() * 0.9,
                            caps=dict(x_show=False, y_show=False, z_show=False),
                            opacity=fit_opacity,
                        ),
                    )
        else:
            fig = go.Figure()
        fig.update_layout(legend=dict(xanchor="left", x=0.01))
        # log scale
        log_dict = {'1D': (invar1_log, outvar_log),
                    '2D': (invar1_log, invar2_log, outvar_log),
                    '2D contour': (invar1_log, invar2_log),
                    '3D': (invar1_log, invar2_log, invar3_log),}
        log_list = ['linear' if log is None or len(log) == 0 else log[0] for log in log_dict[graph_type]]
        log_key = ['xaxis', 'yaxis', 'zaxis']
        comb_dict = dict(zip(log_key, [{'type': log} for log in log_list]))
        if len(log_list) < 3 :
            fig.update_layout(**comb_dict)
        else:
            fig.update_scenes(**comb_dict)
        # color
        if color_use == ['true']: # TODO: trigger-detection no new fig just update
            if fit_use == ['show'] and (graph_type=='2D' and ((fit_color=='output' and color_dd==outvar) or (fit_color=='multi-fit' and color_dd==fit_dd)) or graph_type=='3D'):
                fig.update_traces(
                    marker=dict(
                        coloraxis="coloraxis2",
                        color=indata[color_dd][sel_y] if color_dd in indata.dtype.names else outdata[color_dd][sel_y],
                    ),
                    selector=dict(mode='markers'),
                )
            elif graph_type=='1D':
                fig.update_traces(
                    marker=dict(
                        coloraxis="coloraxis2",
                        color=indata[color_dd][sel_y] if color_dd in indata.dtype.names else outdata[color_dd][sel_y],
                    ),
                    selector=dict(mode='markers'),
                )
                if color_dd==fit_dd:
                    fig.update_layout(coloraxis2=dict(colorscale='cividis', colorbar=dict(title=fit_dd)))
                else:
                    fig.update_layout(coloraxis2=dict(colorscale='plasma', colorbar=dict(title=color_dd)))
            elif graph_type =='2D contour':
                fig.update_traces(
                    marker=dict(
                        coloraxis="coloraxis",
                        color=indata[color_dd][sel_y] if color_dd in indata.dtype.names else outdata[color_dd][sel_y],
                    ),
                    selector=dict(mode='markers'),
                )
                if color_dd == outvar:
                    fig.update_traces(marker_coloraxis="coloraxis2", selector=dict(mode='markers'))
                else:
                    fig.update_layout(coloraxis=dict(colorbar=dict(title=color_dd, x=1.1),
                                                     colorscale='ice'))
            else:
                fig.update_traces(
                    marker=dict(
                        coloraxis="coloraxis",
                        color=indata[color_dd][sel_y] if color_dd in indata.dtype.names else outdata[color_dd][sel_y],
                    ),
                    selector=dict(mode='markers'),
                )
                fig.update_layout(coloraxis=dict(
                    colorbar=dict(title=color_dd, x=1.1),
                    colorscale='viridis',
                ))
        fig.update_layout(height=graph_height)
        return fig


    def mesh_fit(param_slider, id_type, fit_dd, fit_num, param_center, invar_list, invar_log_list, outvar, num_samples, add_noise_var):
        try:  # collecting min/max of slider in filter section
            fit_dd_min, fit_dd_max = param_slider[[i['index'] for i in id_type].index(invars.index(fit_dd))]
        except ValueError:
            fit_dd_min = min(indata[fit_dd])
            fit_dd_max = max(indata[fit_dd])
        if fit_num == 1:
            fit_dd_values = np.array([(fit_dd_max + fit_dd_min) / 2])
        else:
            fit_dd_values = np.linspace(fit_dd_min, fit_dd_max, fit_num)
        for iteration, fit_dd_value in enumerate(fit_dd_values):
            fit_params = [(max(indata[var_invar]) + min(indata[var_invar])) / 2 for var_invar in invars]
            for iter, center_values in enumerate(param_center):
                ind = id_type[iter]['index']
                fit_params[ind] = center_values
            fit_params[invars.index(fit_dd)] = fit_dd_value
            for iter, invar in enumerate(invar_list):
                if invar_log_list[iter] == ['log']:
                    fit_params[invars.index(invar)] = np.logspace(log10(min(indata[invar])), log10(max(indata[invar])),
                                                                  num_samples)
                else:
                    fit_params[invars.index(invar)] = np.linspace(min(indata[invar]), max(indata[invar]), num_samples)
            grid = np.meshgrid(*fit_params)
            x_pred = np.vstack([g.flatten() for g in grid]).T  # extract vector for predict
            sur = Surrogate.load_model(config['fit']['save']) # load surrogate
            try:
                fit_data, fit_var = sur.predict(x_pred, add_noise_var == ['add'])
            except TypeError:
                fit_data, fit_var = sur.predict(x_pred)
                if add_noise_var == ['add']:
                    print('Warning: full data variance not supported') # TODO: fix after PR from Maximilian
            # generated data
            new_mesh_in = np.array([[grid[invars.index(invar)].flatten() for invar in invars]])
            new_mesh_out = np.array([fit_data[:, outvars.index(outvar)]])
            new_mesh_out_std = np.array([np.sqrt(fit_var[:, 0])]) # TODO: use second variance if available
            if iteration == 0:
                mesh_in = new_mesh_in
                mesh_out = new_mesh_out
                mesh_out_std = new_mesh_out_std
            else:
                mesh_in = np.vstack((mesh_in, new_mesh_in))
                mesh_out = np.vstack((mesh_out, new_mesh_out))
                mesh_out_std = np.vstack((mesh_out_std, new_mesh_out_std))
        return mesh_in, mesh_out, mesh_out_std, fit_dd_values

    @app.callback(
        Output('data-table-div', 'style'),
        [Input('show-table', 'n_clicks'),
         Input('hide-table', 'n_clicks'), ]
    )
    def show_table(show, hide):
        ctx = dash.callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        print(trigger_id)
        if trigger_id == 'show-table':
            return {'visibility': 'visible'}
        else:
            return {'visibility': 'hidden'}

    return app
