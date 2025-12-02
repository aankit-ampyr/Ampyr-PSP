# Graph Design Guidelines

Standard visualization patterns for BESS simulation graphs.

## Graph Structure

### Dual Y-Axis Layout
All dispatch graphs use a dual y-axis layout:
- **Primary Y-Axis (Left)**: Power metrics in MW
- **Secondary Y-Axis (Right)**: SOC % and BESS Energy (MWh)

```python
from plotly.subplots import make_subplots
fig = make_subplots(specs=[[{"secondary_y": True}]])
```

## Standard Traces

### 1. Solar (Orange Fill)
```python
fig.add_trace(
    go.Scatter(x=hours, y=solar_mw, name='Solar', fill='tozeroy',
               line=dict(color='#FFA500', width=2),
               hovertemplate='Hour %{x}<br>Solar: %{y:.1f} MW<extra></extra>'),
    secondary_y=False
)
```

### 2. DG Output (Red Fill)
```python
fig.add_trace(
    go.Scatter(x=hours, y=dg_mw, name='DG Output', fill='tozeroy',
               line=dict(color='#DC143C', width=2, shape='hv'),
               fillcolor='rgba(220,20,60,0.3)',
               hovertemplate='Hour %{x}<br>DG Output: %{y} MW<extra></extra>'),
    secondary_y=False
)
```

### 3. BESS Power (Blue Solid)
```python
fig.add_trace(
    go.Scatter(x=hours, y=bess_mw, name='BESS Power',
               line=dict(color='#1f77b4', width=2, shape='hv'),
               hovertemplate='Hour %{x}<br>BESS: %{y:.1f} MW<extra></extra>'),
    secondary_y=False
)
```
- **Positive**: Discharging (power to load)
- **Negative**: Charging (power from solar/DG)

### 4. SOC % (Green Dotted)
```python
fig.add_trace(
    go.Scatter(x=hours, y=soc_pct, name='SOC %',
               line=dict(color='#2E8B57', width=2, dash='dot', shape='hv'),
               hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'),
    secondary_y=True
)
```

### 5. BESS Energy (Royal Blue Dashed)
```python
fig.add_trace(
    go.Scatter(x=hours, y=bess_energy_mwh, name='BESS Energy (MWh)',
               line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
               hovertemplate='Hour %{x}<br>BESS Energy: %{y:.1f} MWh<extra></extra>'),
    secondary_y=True
)
```

### 6. Delivery (Purple Solid, Thick)
```python
fig.add_trace(
    go.Scatter(x=hours, y=delivery_mw, name='Delivery (25 or 0)',
               line=dict(color='purple', width=3, shape='hv'),
               hovertemplate='Hour %{x}<br>Delivery: %{y} MW<extra></extra>'),
    secondary_y=False
)
```

## Reference Lines

### Load Target
```python
fig.add_hline(y=25, line_dash="dash", line_color="gray",
              annotation_text="Load 25 MW", secondary_y=False)
```

### Zero Line
```python
fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)
```

### DG SOC Thresholds
```python
fig.add_hline(y=20, line_dash="dot", line_color="red",
              annotation_text="DG ON (20%)", secondary_y=True)
fig.add_hline(y=80, line_dash="dot", line_color="green",
              annotation_text="DG OFF (80%)", secondary_y=True)
```

### Day Boundary
```python
fig.add_vline(x=24, line_dash="dash", line_color="black", line_width=1,
              annotation_text="Day 2", annotation_position="top")
```

### Hourly Grid Lines
```python
for h in range(48):
    fig.add_vline(x=h, line_dash="dot", line_color="lightgray", line_width=1)
```

## Layout Configuration

```python
fig.update_layout(
    xaxis_title="Hour (0-23: Day 1 | 24-47: Day 2)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=450,
    xaxis=dict(
        showgrid=False,
        tickvals=[0, 6, 12, 18, 24, 30, 36, 42, 47],
        ticktext=['0', '6', '12', '18', '24', '30', '36', '42', '47']
    )
)
fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
fig.update_yaxes(title_text="SOC (%) / BESS Energy (MWh)", secondary_y=True, range=[0, 100])
```

## Color Palette

| Element | Color | Hex Code |
|---------|-------|----------|
| Solar | Orange | #FFA500 |
| DG Output | Crimson | #DC143C |
| BESS Power | Blue | #1f77b4 |
| SOC % | Sea Green | #2E8B57 |
| BESS Energy | Royal Blue | #4169E1 |
| Delivery | Purple | purple |
| Load Target | Gray | gray |
| DG ON threshold | Red | red |
| DG OFF threshold | Green | green |

## Line Styles

| Element | Style | Width |
|---------|-------|-------|
| Solar | Solid fill | 2 |
| DG Output | Step (hv) fill | 2 |
| BESS Power | Step (hv) solid | 2 |
| SOC % | Step (hv) dotted | 2 |
| BESS Energy | Step (hv) dashed | 2 |
| Delivery | Step (hv) solid | 3 |

## Caption Template

```markdown
**Orange**: Solar | **Red**: DG Output | **Blue**: BESS Power (negative=charging) | **Purple**: Delivery

**Green dotted**: SOC % | **Royal Blue dashed**: BESS Energy (MWh)

**Data Source**: Computed from `Inputs/Solar Profile.csv` — [Date Range]

**DG Control**: [Control strategy description]
```

## Complete Example Function

```python
def create_dispatch_graph(hours, solar_mw, dg_mw, bess_mw, soc_pct, bess_energy_mwh, delivery_mw):
    """Create a standard dispatch graph with all traces."""
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Solar (orange fill)
    fig.add_trace(
        go.Scatter(x=hours, y=solar_mw, name='Solar', fill='tozeroy',
                   line=dict(color='#FFA500', width=2),
                   hovertemplate='Hour %{x}<br>Solar: %{y:.1f} MW<extra></extra>'),
        secondary_y=False
    )

    # DG Output (red fill)
    fig.add_trace(
        go.Scatter(x=hours, y=dg_mw, name='DG Output', fill='tozeroy',
                   line=dict(color='#DC143C', width=2, shape='hv'),
                   fillcolor='rgba(220,20,60,0.3)',
                   hovertemplate='Hour %{x}<br>DG Output: %{y} MW<extra></extra>'),
        secondary_y=False
    )

    # BESS Power (blue solid)
    fig.add_trace(
        go.Scatter(x=hours, y=bess_mw, name='BESS Power',
                   line=dict(color='#1f77b4', width=2, shape='hv'),
                   hovertemplate='Hour %{x}<br>BESS: %{y:.1f} MW<extra></extra>'),
        secondary_y=False
    )

    # SOC % (green dotted)
    fig.add_trace(
        go.Scatter(x=hours, y=soc_pct, name='SOC %',
                   line=dict(color='#2E8B57', width=2, dash='dot', shape='hv'),
                   hovertemplate='Hour %{x}<br>SOC: %{y:.1f}%<extra></extra>'),
        secondary_y=True
    )

    # BESS Energy (royal blue dashed)
    fig.add_trace(
        go.Scatter(x=hours, y=bess_energy_mwh, name='BESS Energy (MWh)',
                   line=dict(color='#4169E1', width=2, dash='dash', shape='hv'),
                   hovertemplate='Hour %{x}<br>BESS Energy: %{y:.1f} MWh<extra></extra>'),
        secondary_y=True
    )

    # Delivery (purple thick)
    fig.add_trace(
        go.Scatter(x=hours, y=delivery_mw, name='Delivery',
                   line=dict(color='purple', width=3, shape='hv'),
                   hovertemplate='Hour %{x}<br>Delivery: %{y} MW<extra></extra>'),
        secondary_y=False
    )

    # Reference lines
    fig.add_hline(y=25, line_dash="dash", line_color="gray",
                  annotation_text="Load 25 MW", secondary_y=False)
    fig.add_hline(y=0, line_color="lightgray", line_width=1, secondary_y=False)

    # Day boundary
    fig.add_vline(x=24, line_dash="dash", line_color="black", line_width=1,
                  annotation_text="Day 2", annotation_position="top")

    # Hourly grid
    for h in range(48):
        fig.add_vline(x=h, line_dash="dot", line_color="lightgray", line_width=1)

    # Layout
    fig.update_layout(
        xaxis_title="Hour (0-23: Day 1 | 24-47: Day 2)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=450,
        xaxis=dict(showgrid=False,
                   tickvals=[0, 6, 12, 18, 24, 30, 36, 42, 47],
                   ticktext=['0', '6', '12', '18', '24', '30', '36', '42', '47'])
    )
    fig.update_yaxes(title_text="Power (MW)", secondary_y=False)
    fig.update_yaxes(title_text="SOC (%) / BESS Energy (MWh)", secondary_y=True, range=[0, 100])

    return fig
```

## Usage in Streamlit

```python
fig = create_dispatch_graph(hours, solar_mw, dg_mw, bess_mw, soc_pct, bess_energy_mwh, delivery_mw)
st.plotly_chart(fig, width='stretch')

st.caption("""
**Orange**: Solar | **Red**: DG Output | **Blue**: BESS Power | **Purple**: Delivery

**Green dotted**: SOC % | **Royal Blue dashed**: BESS Energy (MWh)
""")
```
