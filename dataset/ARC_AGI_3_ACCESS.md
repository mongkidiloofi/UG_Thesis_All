# ARC-AGI-3 games and access

ARC-AGI-3 contains **135 games**:

| Set | Games |
| --- | ---: |
| Public | 25 |
| Semi-private | 55 |
| Fully private | 55 |

We can directly access only the **25 public games**. The semi-private and fully private sets are held back for controlled evaluations and competition testing. [Source: official technical report, Table 1](https://arxiv.org/html/2603.24621v2#S3.SS6).

## Access the public games

1. **Play in a browser:** visit the [public game browser](https://arcprize.org/tasks).
2. **Get API access:** sign in at [ARC Prize Platform](https://arcprize.org/platform), open your profile, and create a key under **API Keys**. A registered key unlocks the full public set. [API key guide](https://docs.arcprize.org/api-keys).
3. **List the available games:** set your key and call the discovery endpoint:

   ```bash
   export ARC_API_KEY="your-api-key"
   curl -s https://three.arcprize.org/api/games \
     -H "X-API-Key: $ARC_API_KEY"
   ```

4. **Interact programmatically:** install the official Python toolkit with `pip install arc-agi`, then follow the [quickstart](https://docs.arcprize.org/) or [HTTP playthrough guide](https://docs.arcprize.org/full-play-test) to start a game and submit actions.
