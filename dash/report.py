from dash import Dash, html, dcc, dash_table, Output, Input, State
import plotly.express as px
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc
import engineering


def report_player(df, app):
    report = Report(df, app)
    return dbc.Card(
        dbc.CardBody([
            report()
        ])
    )


def get_history(player_df):
    ret = [dbc.Row([dbc.Col('Year'), dbc.Col('Team'), dbc.Col('Salary')], className='text-center')]
    for idx, row in player_df.iterrows():
        ret.append(dbc.Row([
            dbc.Col(row['year'], className='text-center'),
            dbc.Col(row['Team'], className='text-center'),
            dbc.Col('£'+format(int(row['Base Salary']), ',d'))
        ]))

    return ret


class BaseBlock:
    def __init__(self, app=None, prefix=''):
        self.app = app
        self.prefix = prefix

        if self.app is not None and hasattr(self, 'callbacks'):
            self.callbacks(self.app)


class Profile:
    def __init__(self, df, player_name):
        self._df = df
        self._player_name = player_name

    @property
    def player_df(self):
        return self._df[self._df['Name'] == self._player_name]

    def render(self):
        player_df = self.player_df.sort_values(by='year')
        return dbc.Card(dbc.Row([
            # image div
            dbc.Col(dbc.CardImg(src=f"https://d2zywfiolv4f83.cloudfront.net/img/players/{player_df['Player Id'].values[-1]}.jpg", top=True),width=2),

            # info div
            ## position
            ## birth year
            ## team
            dbc.Col(html.Div([
                html.H4(f'이름: {self._player_name}', className="card-title", style={'margin-bottom':'10px'}),
                html.P(f"출생: {player_df['Birth Year'].values[-1]}", className="card-text",),
                html.P(f"포지션: {player_df['Position'].values[-1]}", className="card-text",),
                html.P(f"소속: {player_df['Team'].values[-1]}", className="card-text",)
            ]), width=4, align='center'),

            # history
            ## 연도 - 팀 - 연봉
            dbc.Col(html.Div([*get_history(player_df)]), width=4, className='text-end')
        ]))


class Analysis(BaseBlock):
    def __init__(self, df, profile, app):
        super().__init__(app, 'Analysis')
        self._profile = profile
        self.sample_data = df

    def callbacks(self, app):
        @app.callback(
            Output(component_id='offensive-graph', component_property='figure'),
            Input(component_id='offensive-radio-item', component_property='value')
        )
        def update_offensive(y_col_chosen):
            position = self._profile.player_df['Position'].to_list()[0]
            fig = px.line(
                x=engineering.age_order,
                y=self.sample_data.groupby(['Position', 'Age Lev']).mean(numeric_only=True).loc[position, y_col_chosen],
                markers=True
            )
            fig.add_scatter(x=self._profile.player_df['Age Lev'], y=self._profile.player_df[y_col_chosen], mode='lines+markers')

            return fig

        @app.callback(
            Output(component_id='defensive-graph', component_property='figure'),
            Input(component_id='defensive-radio-item', component_property='value')
        )
        def update_defensive(y_col_chosen):
            position = self._profile.player_df['Position'].to_list()[0]
            fig = px.line(
                x=engineering.age_order,
                y=self.sample_data.groupby(['Position', 'Age Lev']).mean(numeric_only=True).loc[position, y_col_chosen],
                markers=True
            )
            fig.add_scatter(x=self._profile.player_df['Age Lev'], y=self._profile.player_df[y_col_chosen], mode='lines+markers')

            return fig

    def render(self):
        return dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.RadioItems(
                        options=[{"label": x, "value": x} for x in Report.feature_position[f"{self._profile.player_df['Position'].to_list()[0]}-o"]],
                        value=Report.feature_position[f"{self._profile.player_df['Position'].to_list()[0]}-o"][0],
                        id='offensive-radio-item',
                        inline=True
                    )
                ]),
                dbc.Row([dcc.Graph(figure={}, id='offensive-graph')], className="h-20")
            ], width=5, className="h-75"),
            dbc.Col([
                dbc.Row([
                    dbc.RadioItems(
                        options=[{"label": x, "value": x} for x in Report.feature_position[f"{self._profile.player_df['Position'].to_list()[0]}-d"]],
                        value=Report.feature_position[f"{self._profile.player_df['Position'].to_list()[0]}-d"][0],
                        id='defensive-radio-item',
                        inline=True
                    )
                ]),
                dbc.Row([dcc.Graph(figure={}, id='defensive-graph')], className="h-20")
            ], width=5, className="h-75")
        ])


class Report(BaseBlock):
    feature_position = {
        'Forward-o': ['G', 'xG', 'NPG', 'A', 'xA', 'Drb_Off'],
        'Forward-d': ['Tackles', 'Inter'],
        'Midfielder-o': ['G', 'xG', 'A', 'xA', 'xGBuildup', 'KeyP', 'Drb_Off', 'AvgP', 'PS%'],
        'Midfielder-d': ['Tackles', 'Inter', 'Clear', 'Blocks'],
        'Defender-o': ['G', 'xG', 'A', 'xA', 'xGBuildup', 'AvgP', 'PS%'],
        'Defender-d': ['Tackles', 'Inter', 'Clear', 'Blocks', 'Drb_Def'],
        'Goalkeeper-o': ['xGBuildup', 'AvgP', 'PS%'],
        'Goalkeeper-d': ['Tackles', 'Inter', 'Clear', 'Blocks', 'Drb_Def']
    }

    def __init__(self, eda_df, app, mins=1000):
        super().__init__(app, 'report')
        self._app = app
        self.sample_data = eda_df[eda_df['Min'] > mins]
        self._profile = Profile(self.sample_data, 'Son Heung-Min')
        self._analysis = Analysis(self.sample_data, self._profile, app)

    def __call__(self, *args, **kwargs):
        return self.render()

    def salary_top100(self):
        threshold = 100
        s_eda_df = self.sample_data.sort_values(by='Base Salary', ascending=False)
        return s_eda_df[~s_eda_df.duplicated(subset='Name', keep='first')].iloc[:threshold]['Name'].to_list()

    def callbacks(self, app):
        @app.callback(
            Output("collapse", "is_open"),
            [Input("collapse-button", "n_clicks")],
            [State("collapse", "is_open")],
        )
        def toggle_collapse(n, is_open):
            if n:
                return not is_open
            return is_open

        @app.callback(
            Output("player_profile", "children"), [Input(component_id="player-select", component_property='value')]
        )
        def select_name(name):
            if name:
                self._profile = None
                self._profile = Profile(self.sample_data, name)
            return self._profile.render()

        @app.callback(
            Output("player_analysis", "children"), [Input(component_id="player-select", component_property='value')]
        )
        def select_name(name):
            if name:
                self._analysis = None
                self._analysis = Analysis(self.sample_data, self._profile, self._app)
            return self._analysis.render()

    def render(self):
        return html.Div([
            dbc.Row([
                dbc.Col(dbc.Select(
                    id="player-select",
                    options=[{'label': name, 'value': name} for name in self.salary_top100()],
                    value="Son Heung-Min"
                )),

                dbc.Col(dbc.Button(
                    "Profile",
                    id="collapse-button",
                    className="btn btn-secondary",
                    n_clicks=0,
                ))
            ]),
            dbc.Collapse(
                html.Div(id='player_profile'),
                id="collapse",
                is_open=False,
            ),
            html.Div(id='player_analysis'),

        ])
