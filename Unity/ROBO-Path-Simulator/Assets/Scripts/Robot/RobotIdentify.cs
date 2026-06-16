using UnityEngine;

public enum RobotPlatform 
{ 
    Wheeled, 
    Legged 
}

public class RobotIdentify : MonoBehaviour
{
    public RobotPlatform platform;
}
