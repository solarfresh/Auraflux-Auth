class Queue:
    IAM = 'iam'
    AGENT = 'agent'


class AgentRequest:
    name = "handle_agent_request"
    queue = Queue.AGENT


class UpdateModelFamilies:
    name = "update_model_families"
    queue = Queue.IAM
