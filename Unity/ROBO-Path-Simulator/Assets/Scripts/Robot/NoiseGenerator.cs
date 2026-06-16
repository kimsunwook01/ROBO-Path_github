namespace ROBOPath.Robot
{
    public interface INoiseGenerator
    {
        float GetNoise(float range);
    }

    public class UniformNoiseGenerator : INoiseGenerator
    {
        private System.Random random;

        public UniformNoiseGenerator()
        {
            random = new System.Random();
        }

        public UniformNoiseGenerator(int seed)
        {
            random = new System.Random(seed);
        }

        public float GetNoise(float range)
        {
            if (range <= 0f) return 0f;
            // Uniform noise in [-range, range]
            float r = (float)random.NextDouble();
            return (r * 2f * range) - range;
        }
    }
}
