using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

public class SamplePlayModeTest
{
    [UnityTest]
    public IEnumerator SamplePlayModeTestWithEnumeratorPasses()
    {
        yield return null;
        Assert.IsTrue(true);
    }
}
