using UnityEngine;
using System.IO;
using Newtonsoft.Json.Linq;

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
        private static JObject configRoot = null;
        public static INoiseGenerator noiseGenerator = new UniformNoiseGenerator(); // Default DI

        public static void SetNoiseGenerator(INoiseGenerator generator)
        {
            noiseGenerator = generator;
        }

        private static void LoadConfig()
        {
            if (configRoot != null) return;
            // 단일 원본 원칙: 저장소 루트 config/cost_profiles.json 을 직접 읽음
            string path = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../config/cost_profiles.json"));
            if (File.Exists(path))
            {
                string json = File.ReadAllText(path);
                ParseConfig(json);
            }
            else
            {
                Debug.LogWarning($"[FeedbackCalculator] config file not found at {path}");
                configRoot = new JObject(); // Prevent repeated loading
            }
        }

        private static void ParseConfig(string json)
        {
            configRoot = JObject.Parse(json);
            JToken nr = configRoot["noise_range"];
            if (nr != null && nr.Type != JTokenType.Null)
            {
                noiseRange = nr.Value<float>();
            }
        }

        // Only for testing — allows injecting mock JSON without touching the filesystem
        public static void SetJsonContentForTest(string json)
        {
            ParseConfig(json);
        }

        public static FeedbackMetrics ComputeMetrics(RobotPlatform platform, string terrainTag)
        {
            LoadConfig();
            FeedbackMetrics metrics = new FeedbackMetrics { Traversable = true, L = 0.5f, S = 0.5f, E = 0.5f };

            if (configRoot == null || !configRoot.HasValues)
                return metrics;

            string platformKey = platform.ToString().ToLowerInvariant();

            // Navigate: platforms -> {platformKey} -> terrains -> {terrainTag}
            JToken terrainToken = configRoot.SelectToken($"platforms.{platformKey}.terrains.{terrainTag}");
            if (terrainToken == null || terrainToken.Type != JTokenType.Object)
                return metrics; // Use defaults if terrain not found

            JObject terrain = (JObject)terrainToken;

            // Check traversable flag
            JToken traversableToken = terrain["traversable"];
            if (traversableToken != null && traversableToken.Type == JTokenType.Boolean && !traversableToken.Value<bool>())
            {
                metrics.Traversable = false;
                metrics.L = null;
                metrics.S = null;
                metrics.E = null;
                return metrics;
            }

            // Check if L/S/E are null (e.g. Path_Stair for wheeled)
            JToken lToken = terrain["L"];
            JToken sToken = terrain["S"];
            JToken eToken = terrain["E"];

            if (lToken == null || lToken.Type == JTokenType.Null ||
                sToken == null || sToken.Type == JTokenType.Null ||
                eToken == null || eToken.Type == JTokenType.Null)
            {
                metrics.Traversable = false;
                metrics.L = null;
                metrics.S = null;
                metrics.E = null;
                return metrics;
            }

            float baseL = lToken.Value<float>();
            float baseS = sToken.Value<float>();
            float baseE = eToken.Value<float>();

            // Add noise and clamp
            metrics.L = Mathf.Clamp(baseL + noiseGenerator.GetNoise(noiseRange), 0f, 1f);
            metrics.S = Mathf.Clamp(baseS + noiseGenerator.GetNoise(noiseRange), 0f, 1f);
            float noisyE = baseE + noiseGenerator.GetNoise(noiseRange);
            metrics.E = noisyE < 0f ? 0f : noisyE; // E has no upper bound clamp (intentional per spec)

            return metrics;
        }
    }
}
