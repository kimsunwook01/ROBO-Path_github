using System;
using System.Text.RegularExpressions;

public class Program {
    public static void Main() {
        string jsonContent = @"{
                ""noise_range"": 0.05,
                ""platforms"": {
                    ""wheeled"": {
                        ""terrains"": {
                            ""Terrain_Flat"": { ""L"": 0.1, ""S"": 0.95, ""E"": 0.95, ""traversable"": true },
                            ""Path_Stair"": { ""L"": null, ""S"": null, ""E"": null, ""traversable"": false }
                        }
                    },
                    ""legged"": {
                        ""terrains"": {
                            ""Path_Stair"": { ""L"": 0.45, ""S"": 0.70, ""E"": 0.65, ""traversable"": true }
                        }
                    }
                }
            }";
        string platformKey = "wheeled";
        string terrainTag = "Terrain_Flat";

        int platformIdx = jsonContent.IndexOf("\"" + platformKey + "\"");
        Console.WriteLine("platformIdx: " + platformIdx);
        int nextPlatformIdx = jsonContent.IndexOf("\"legged\"", platformIdx + 1);
        string platformBlock = jsonContent.Substring(platformIdx, nextPlatformIdx - platformIdx);
        Console.WriteLine("platformBlock: " + platformBlock);
        int terrainIdx = platformBlock.IndexOf("\"" + terrainTag + "\"");
        Console.WriteLine("terrainIdx: " + terrainIdx);
        int nextTerrainIdx = platformBlock.IndexOf("}", terrainIdx);
        string terrainBlock = platformBlock.Substring(terrainIdx, nextTerrainIdx - terrainIdx + 1);
        Console.WriteLine("terrainBlock: " + terrainBlock);

        float L = ParseFloat(terrainBlock, "L", 0.5f);
        Console.WriteLine("L: " + L);
    }
    private static float ParseFloat(string block, string key, float defaultVal)
    {
        Match m = Regex.Match(block, "\"" + key + "\"\\s*:\\s*([0-9\\.]+)");
        if (m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float val))
        {
            return val;
        }
        return defaultVal;
    }
}
