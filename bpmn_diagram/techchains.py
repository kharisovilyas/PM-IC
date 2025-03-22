from networkx import *

operations = [str(i) for i in range(7)]
matrix = [
    ["0","1","1","0","0","0","0"],
    ["1","0","0","1","1","0","0"],
    ["1","0","0","1","0","0","0"],
    ["0","1","1","0","1","1","1"],
    ["0","1","0","1","0","0","1"],
    ["0","0","0","1","0","0","0"],
    ["0","0","0","1","1","0","0"],
    ]
start = "0"
finish = "4"
def is_next_operation(operation, kandidat_operation):
    '''Проверка является ли kandidat_operation той операцией, которая может идти следом за operation'''
    return matrix[int(kandidat_operation)][int(operation)]=="1"

##############################################################

def get_all_ways(start, finish, is_next_operation, operations=None, DG:DiGraph=None):
    '''Либо список операций либо ориентированный граф'''
    ways = []
    st = []

    def proverka():
        res = True
        for i in range(len(ways)):
            if ways[i][len(ways[i])-1] != finish:
                res = False
                break
        return res

    def wayexist(x,way):
        res = False
        for i in range(len(ways[way])):
            if (ways[way][len(ways[way])-1-i] == x):
                res = True
                break
        return res

    def fillstack(y):
        operation = ways[y][len(ways[y])-1]    # отправная операция для поиска куда бы из нее сходить
        if operations:
            for kandidat_operation in operations:  # ищем операцию, которая могла бы быть следующей в цепочке
                if (is_next_operation(operation, kandidat_operation) and not(wayexist(kandidat_operation,y))):   # ищем в матрице (можем сходить) и что там мы еще не были
                    st.append(kandidat_operation)
        elif DG:
            if operation in DG.nodes:
                for kandidat_operation in DG.neighbors(operation):  # ищем операцию, которая могла бы быть следующей в цепочке
                    if (is_next_operation(operation, kandidat_operation) and not(wayexist(kandidat_operation,y))):   # ищем в матрице (можем сходить) и что там мы еще не были
                        st.append(kandidat_operation)

    def copyway(i,x):
        tmp = []
        for j in range(len(ways[i])):
            tmp.append(ways[i][j])
        tmp[len(tmp)-1] = x
        ways.append(tmp)

    ways.append([start])
    ii = 0
    while (not proverka()):
        if ii >= len(ways): ii=0
        if not(ways[ii][len(ways[ii])-1] == finish):
            fillstack(ii)
            if len(st) == 0:
                ways.pop(ii)
            else:
                tmp = st.pop()
                ways[ii].append(tmp)
                while not(len(st) == 0):
                    tmp = st.pop()
                    copyway(ii,tmp)
        ii += 1
    return ways

if __name__ == '__main__':
    ways = get_all_ways(operations, start=start, finish=finish, is_next_operation=is_next_operation)
    print(ways)