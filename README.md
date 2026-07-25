# Mini airways maps generator
Generate maps of real-world airports by ICAO code in game "Mini Airways"

![](https://shields.io/badge/dependencies-Python_3.14-blue)
![](https://shields.io/badge/dependencies-PowerShell_7-navy)

## Acknowledgement

| Data source                                                  | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [Navigraph Unlimited](https://navigraph.com/pricing)         | [Paid service] It needs to be active when updating the database. The database must exist but can be outdated when running the program. |
| [Airport codes](https://airportsbase.org/ICAO.php)           | The program depends (embeds) the data source. If the website is not available anymore, the program cannot run. |
| [Open street map](https://www.openstreetmap.org/copyright)   | The program depends (embeds) the data source. If the website is not available anymore, the program cannot run. |
| [Airport code database search](https://www.avcodes.co.uk/aptcodesearch.asp) | Recommended but not required. It is a convenient tool to find ICAO code of an airport, while users can remember or use alternative source to find ICAO code. |



## Install

When subscribed Navigraph Unlimited, in the subscription account, download [FMS Data Manager](https://navigraph.com/downloads).

In "Addon Mappings" tab, add an "Little NavMap" addon and install to user defined folder.

![image-20260722182607471](./assets/image-20260722182607471.png)

In "Addon List" tab, download this item.

![image-20260722183106918](./assets/image-20260722183106918.png)

In the installation options, let the user defined folder be `$navmap`, which will be referred below.

[Database schema](https://github.com/albar965/atools/blob/master/resources/sql/fs/db/create_ap_schema.sql)

Create a Python virtual environment and activate.

Run the following command.

```
pip install -r requirements.txt
```



## Usage

Run the following command with arguments in PowerShell 7.

```
python main.py
```

Arguments:

| Argument                | Required? | Data Type | Description                                                  |
| ----------------------- | --------- | --------- | ------------------------------------------------------------ |
| `--db_path`             | ✓         | str       | Path to Little NavMap database, which is `$navmap/little_navmap_db`. |
| `--icao`                | ✓         | str       | [ICAO code](https://www.avcodes.co.uk/aptcodesearch.asp) of airport. |
| `--min_cam_size`        |           | float     | Initial camera size, artificial unit defined by game developer. Default: 6.5. |
| `--max_cam_size`        |           | float     | Camera size after applying maximum times of the airspace expansion, artificial unit defined by game developer. Default: 10.5. |
| `--vertical_resolution` |           | int       | Vertical pixels of the background map. Aspect ratio is fixed to 16:9. If actual screen resolution is smaller than it, the game can down-sampled automatically. Default: 1440 (represents 2560*1440 resolution). |



>   [!note]
>
>   Runways identifier different from real-world.
>
>   In Mini Airways, runways identifier is retrieved from true heading; while in real world, runways identifier is defined by magnetic heading.

