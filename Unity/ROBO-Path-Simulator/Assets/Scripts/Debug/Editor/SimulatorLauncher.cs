using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// 헤드리스(배치모드) 시뮬레이터 진입점.
///
/// run_simulator.sh 가 다음과 같이 호출한다:
///   Unity -batchmode -nographics -projectPath ... \
///         -executeMethod SimulatorLauncher.RunHeadless -logFile .../simulator.log
///
/// -executeMethod 는 전역 네임스페이스의 정적 메서드를 기대하므로, 가이드 §6.1 과
/// 정확히 일치하도록 이 클래스는 의도적으로 네임스페이스 없이 전역에 둔다.
/// (UnityEditor API 를 사용하므로 반드시 Editor 폴더 하위에 위치해야 한다.)
///
/// ⚠️ 실 Mac 검증 필요:
///   - 배치모드에서 Play 모드를 무한 구동하는 것은 환경 의존성이 있다. 실제 Mac 러너에서
///     물리/Update 틱이 도는지, 종료(kill/launchctl)가 정상 동작하는지 반드시 확인할 것.
///   - run_simulator.sh 는 -quit 를 주지 않으므로 executeMethod 반환 후에도 Editor 가
///     살아 있고, 아래 EnterPlaymode 로 시뮬레이션이 구동된다. 프로세스 종료는
///     launchd(kickstart -k) 또는 외부 kill 로 처리한다.
///   - 의미 있는 헤드리스 동작을 위해 메인 씬에 RobotSpawner / SubprocessTelemetrySink /
///     WebSocketServer 등 구동 오브젝트가 배치되어 있어야 한다.
/// </summary>
public static class SimulatorLauncher
{
    // 헤드리스로 띄울 메인 씬 (대규모 캠퍼스 맵)
    private const string MainScenePath = "Assets/Scenes/CampusMainMap.unity";

    public static void RunHeadless()
    {
        Debug.Log("[SimulatorLauncher] RunHeadless invoked");

        if (!System.IO.File.Exists(MainScenePath))
        {
            Debug.LogError($"[SimulatorLauncher] 메인 씬을 찾을 수 없음: {MainScenePath}");
            EditorApplication.Exit(1);
            return;
        }

        try
        {
            EditorSceneManager.OpenScene(MainScenePath, OpenSceneMode.Single);
            Debug.Log($"[SimulatorLauncher] 씬 로드 완료: {MainScenePath}");
        }
        catch (System.Exception ex)
        {
            Debug.LogError($"[SimulatorLauncher] 씬 로드 실패: {ex.Message}\n{ex.StackTrace}");
            EditorApplication.Exit(1);
            return;
        }

        // executeMethod 가 동기 반환된 직후(다음 에디터 틱)에 안전하게 플레이 모드로 진입한다.
        // (executeMethod 콜스택 내부에서 곧바로 EnterPlaymode 를 호출하면 버전에 따라
        //  거부될 수 있어 delayCall 로 한 틱 미룬다.)
        EditorApplication.delayCall += () =>
        {
            Debug.Log("[SimulatorLauncher] 헤드리스 플레이 모드 진입");
            EditorApplication.EnterPlaymode();
        };
    }
}
