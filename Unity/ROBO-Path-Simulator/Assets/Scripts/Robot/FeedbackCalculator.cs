using UnityEngine;
using System.IO;
using System.Text.RegularExpressions;

namespace ROBOPath.Robot
{
    public struct FeedbackMetrics
    {
        public float? L;
        public float? S;
        public float? E;
        public bool Traversable;
    }

    public static class FeedbackCalculator
    {
        private static float noiseRange = 0.05f;
        private static string jsonContent = null;
        public static INoiseGenerator noiseGenerator = new UniformNoiseGenerator(); // Default DI

        public static void SetNoiseGenerator(INoiseGenerator generator)
        {
            noiseGenerator = generator;
        }

        private static void LoadConfig()
        {
            if (jsonContent != null) return;
            string path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../config/cost_profiles.json"));
            if (File.Exists(path))
            {
                jsonContent = File.ReadAllText(path);
                
                // Parse noise_range
                Match m = Regex.Match(jsonContent, @"""noise_range""\s*:\s*([0-9\.]+)");
                if (m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float nr))
                {
                    noiseRange = nr;
                }
            }
            else
            {
                Debug.LogWarning($"[FeedbackCalculator] config file not found at {path}");
                jsonContent = ""; // Prevent repeated loading
            }
        }

        // Only for testing
        public static void SetJsonContentForTest(string json)
        {
            jsonContent = json;
            Match m = Regex.Match(jsonContent, @"""noise_range""\s*:\s*([0-9\.]+)");
            if (m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float nr))
            {
                noiseRange = nr;
            }
        }

        public static FeedbackMetrics ComputeMetrics(RobotPlatform platform, string terrainTag)
        {
            LoadConfig();
            FeedbackMetrics metrics = new FeedbackMetrics { Traversable = true, L = 0.5f, S = 0.5f, E = 0.5f };

            if (string.IsNullOrEmpty(jsonContent))
                return metrics;

            string platformKey = platform.ToString().ToLowerInvariant();
            
            // Extract the platform block
            int platformIdx = jsonContent.IndexOf($@"""{platformKey}""");
            if (platformIdx == -1) return metrics;

            int nextPlatformIdx = jsonContent.IndexOf(@"""legged""", platformIdx + 1);
            if (nextPlatformIdx == -1) nextPlatformIdx = jsonContent.IndexOf(@"""wheeled""", platformIdx + 1);
            if (nextPlatformIdx == -1) nextPlatformIdx = jsonContent.Length;

            string platformBlock = jsonContent.Substring(platformIdx, nextPlatformIdx - platformIdx);

            // Extract the terrain block
            int terrainIdx = platformBlock.IndexOf($@"""{terrainTag}""");
            if (terrainIdx == -1) return metrics; // Use defaults if terrain not found

            int nextTerrainIdx = platformBlock.IndexOf("}", terrainIdx);
            string terrainBlock = platformBlock.Substring(terrainIdx, nextTerrainIdx - terrainIdx + 1);

            // Check if traversable is false or L is null
            if (terrainBlock.Contains(@"""traversable"": false") || terrainBlock.Contains(@"""L"": null"))
            {
                metrics.Traversable = false;
                metrics.L = null;
                metrics.S = null;
                metrics.E = null;
                return metrics;
            }

            // Parse L, S, E
            metrics.L = ParseFloat(terrainBlock, "L", 0.5f);
            metrics.S = ParseFloat(terrainBlock, "S", 0.5f);
            metrics.E = ParseFloat(terrainBlock, "E", 0.5f);

            // Add noise and clamp
            metrics.L = Mathf.Clamp(metrics.L.Value + noiseGenerator.GetNoise(noiseRange), 0f, 1f);
            metrics.S = Mathf.Clamp(metrics.S.Value + noiseGenerator.GetNoise(noiseRange), 0f, 1f);
            metrics.E = metrics.E.Value + noiseGenerator.GetNoise(noiseRange); // E has no upper bound clamp, but should it be >= 0? Let's just leave as is or clamp min 0.
            if (metrics.E.Value < 0f) metrics.E = 0f;

            return metrics;
        }

        private static float ParseFloat(string block, string key, float defaultVal)
        {
            Match m = Regex.Match(block, $@"""{key}""\s*:\s*([0-9\.]+)");
            if (m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float val))
            {
                return val;
            }
            return defaultVal;
        }
    }
}
