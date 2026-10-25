import sys, os, time, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.services import supervisor_service, swarm_service

EVAL_TASKS = [
    {'id': 'T1', 'goal': '列出 scripts 目录下的文件名', 'max_wait': 120},
    {'id': 'T2', 'goal': '统计 core/services 目录下有多少个 .py 文件', 'max_wait': 120},
    {'id': 'T3', 'goal': '读 core/services/message_service.py 的调度者回执段，改成调 LLM 生成回执', 'max_wait': 300},
    {'id': 'T4', 'goal': '给红包功能加一个查看已发红包记录的接口', 'max_wait': 600},
    {'id': 'T5', 'goal': '把 SASES 文件上传的前端打通', 'max_wait': 900},
]

USER_ID = 2
SUPERVISOR_ID = 'sases_assistant_2'
ONLY = sys.argv[1] if len(sys.argv) > 1 else 'all'


async def run_one(task):
    conv_id = 40 + EVAL_TASKS.index(task)
    print('\n=== 开始 ' + task['id'] + ': ' + task['goal'][:50] + ' ===')
    start = time.time()
    run_id = supervisor_service.create_run(USER_ID, conv_id, SUPERVISOR_ID, task['goal'])
    print('[' + task['id'] + '] run_id=' + str(run_id) + ' conv_id=' + str(conv_id))
    try:
        _pt = await swarm_service.plan_task(
            user_id=USER_ID,
            conversation_id=conv_id,
            user_input=task['goal'],
            supervisor_id=SUPERVISOR_ID,
            supervisor_run_id=run_id,
        )
        print('[' + task['id'] + '] plan_task 返回: ' + str(_pt))
    except Exception as e:
        print('[' + task['id'] + '] plan_task 失败: ' + str(e))
    while time.time() - start < task['max_wait']:
        time.sleep(5)
        run = supervisor_service.get_run(run_id)
        if not run:
            continue
        if run['status'] != 'running':
            elapsed = int(time.time() - start)
            return {'id': task['id'], 'status': run['status'], 'rounds': run['current_round'], 'credits': run['credits_used'], 'elapsed': elapsed}
    supervisor_service.cancel_run(run_id, USER_ID)
    return {'id': task['id'], 'status': 'timeout', 'elapsed': task['max_wait']}


async def main():
    results = []
    for task in EVAL_TASKS[:2]:
        if ONLY != 'all' and task['id'] != ONLY:
            continue
        r = await run_one(task)
        results.append(r)
        print('[' + task['id'] + '] 结果: ' + str(r))
    with open('eval_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\n=== 结果写入 eval_results.json ===')


if __name__ == '__main__':
    asyncio.run(main())
