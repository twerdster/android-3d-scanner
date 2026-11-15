"""Record untouched historical build entry attempts using trusted local Java."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sdk',type=Path);args=parser.parse_args()
    output=ROOT/'updated/build/historical-attempt'; output.mkdir(parents=True,exist_ok=True)
    studio=ROOT/'versions/android-studio'
    attempts=[]
    commands=[('studio-wrapper-entry',['java','-cp','gradle/wrapper/gradle-wrapper.jar',
       'org.gradle.wrapper.GradleWrapperMain','assembleDebug'],studio),
       ('submitted-source-compile',['javac','-encoding','UTF-8','-Xmaxerrs','8','-d',str(output),
        *[str(p) for p in sorted((ROOT/'source/src').rglob('*.java'))]],ROOT)]
    if args.sdk:
        platform=args.sdk/'platforms/android-35/android.jar'
        commands.append(('submitted-source-with-api35',['javac','-encoding','UTF-8','-Xmaxerrs','12',
          '-classpath',str(platform),'-d',str(output),
          *[str(p) for p in sorted((ROOT/'source/src').rglob('*.java'))]],ROOT))
    def portable(text):
        text=text.replace(str(ROOT),'<repo>')
        if args.sdk:text=text.replace(str(args.sdk),'<android-sdk>')
        return text
    for name,command,cwd in commands:
        result=subprocess.run(command,cwd=cwd,text=True,capture_output=True)
        attempts.append({'name':name,'command':[portable(a) for a in command],
          'working_directory':str(cwd.relative_to(ROOT)) or '.', 'exit_code':result.returncode,
          'output':portable(result.stdout+result.stderr)})
    data={'schema':'beam-historical-build-attempt-v1','attempts':attempts,
      'java':subprocess.run(['java','-version'],capture_output=True,text=True).stderr.strip(),
      'available_gradle_command':bool(shutil.which('gradle')),
      'android_sdk_api35_available':bool(args.sdk and (args.sdk/'platforms/android-35/android.jar').exists()),
      'missing_studio_inputs':[p for p in ['gradle/wrapper/gradle-wrapper.jar','openCVLibrary246',
          'openCVLibrary2410','app/proguard-rules.txt'] if not (studio/p).exists()],
      'result':'Historical Android build blocked; no APK produced. Desktop adapter validation is separate.',
      'execution_policy':'Trusted java/javac only; archived wrapper scripts and archived binaries were not executed.'}
    target=ROOT/'validation/historical-build-attempt.json'; target.write_text(json.dumps(data,indent=2)+'\n')
    print('Historical build blocked; details: validation/historical-build-attempt.json')

if __name__=='__main__':main()
