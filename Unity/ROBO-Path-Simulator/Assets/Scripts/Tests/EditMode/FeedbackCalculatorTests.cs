using NUnit.Framework;
using ROBOPath.Robot;

namespace ROBOPath.Tests.EditMode
{
    public class MockNoiseGenerator : INoiseGenerator
    {
        public float noiseValueToReturn = 0f;
        public float GetNoise(float range) => noiseValueToReturn;
    }

    public class FeedbackCalculatorTests
    {
        [SetUp]
        public void Setup()
        {
            string mockJson = @"{
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
            FeedbackCalculator.SetJsonContentForTest(mockJson);
        }

        [Test]
        public void Wheeled_TerrainFlat_ReturnsCorrectBaseValues()
        {
            var noiseMock = new MockNoiseGenerator { noiseValueToReturn = 0f };
            FeedbackCalculator.SetNoiseGenerator(noiseMock);

            var metrics = FeedbackCalculator.ComputeMetrics(RobotPlatform.Wheeled, "Terrain_Flat");
            
            Assert.IsTrue(metrics.Traversable);
            Assert.AreEqual(0.1f, metrics.L);
            Assert.AreEqual(0.95f, metrics.S);
            Assert.AreEqual(0.95f, metrics.E);
        }

        [Test]
        public void Wheeled_PathStair_ReturnsUntraversable()
        {
            var noiseMock = new MockNoiseGenerator { noiseValueToReturn = 0f };
            FeedbackCalculator.SetNoiseGenerator(noiseMock);

            var metrics = FeedbackCalculator.ComputeMetrics(RobotPlatform.Wheeled, "Path_Stair");
            
            Assert.IsFalse(metrics.Traversable);
            Assert.IsNull(metrics.L);
        }

        [Test]
        public void NoiseInjection_AffectsValues()
        {
            var noiseMock = new MockNoiseGenerator { noiseValueToReturn = 0.04f };
            FeedbackCalculator.SetNoiseGenerator(noiseMock);

            var metrics = FeedbackCalculator.ComputeMetrics(RobotPlatform.Legged, "Path_Stair");
            
            Assert.IsTrue(metrics.Traversable);
            Assert.AreEqual(0.45f + 0.04f, metrics.L.Value, 0.001f);
        }
    }
}
