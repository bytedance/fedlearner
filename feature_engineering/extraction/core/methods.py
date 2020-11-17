from core.extract import Operator


class Cross(Operator):
    def __init__(self):
        super(Cross, self).__init__(feature_name='Cross')

    def __call__(self, input_dict: dict) -> str:
        dict_values = list(input_dict.values())
        assert len(dict_values) == 2, 'Operator "Cross" requires 2 input values, but got {}.'.format(len(dict_values))
        return '{}_{}'.format(dict_values[0], dict_values[1])


class MatchList(Operator):
    def __init__(self):
        super(MatchList, self).__init__(feature_name='MatchList')

    def __call__(self, feature: str, feature_list: [str]):
        try:
            pos = feature_list.index(feature)
        except ValueError:
            return None
        return pos + 1


class MatchLists(Operator):
    def __init__(self):
        super(MatchLists, self).__init__(feature_name='MatchLists')

    def __call__(self, feature_list1: str, feature_list2: str):
        return len(set(feature_list1) & set(feature_list2))


class MatchRank(Operator):
    def __init__(self):
        super(MatchRank, self).__init__(feature_name='MatchRank')

    def __call__(self, feature: str, deal_list: [tuple]):
        for i, tp in enumerate(deal_list):
            if tp[0] == feature:
                return i
        return None


class MatchMap(Operator):
    def __init__(self):
        super(MatchMap, self).__init__(feature_name='MatchMap')

    def __call__(self, feature: str, deal_list: [tuple]):
        for tp in deal_list:
            if tp[0] == feature:
                return tp[1]
        return None
